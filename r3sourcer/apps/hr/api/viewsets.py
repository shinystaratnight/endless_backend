import decimal
import datetime
import logging
import operator

from functools import reduce

from django.conf import settings
from django.db import transaction
from django.db.models import Q, Case, When, BooleanField, Value, IntegerField, F, Sum, Max
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import ugettext_lazy as _
from rest_framework import exceptions, mixins, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.viewsets import GenericViewSet
from filer.models import File

from r3sourcer.apps.candidate import models as candidate_models
from r3sourcer.apps.core.api.fields import ApiBaseRelatedField
from r3sourcer.apps.core.api.mixins import GoogleAddressMixin
from r3sourcer.apps.core.api.viewsets import BaseApiViewset, BaseViewsetMixin
from r3sourcer.apps.core.utils.text import format_lazy
from r3sourcer.apps.core.models import Role, Address
from r3sourcer.apps.core_adapter import constants
from r3sourcer.apps.hr import models as hr_models, payment
from r3sourcer.apps.hr.api.filters import TimesheetFilter
from r3sourcer.apps.hr.api.serializers import timesheet as timesheet_serializers, job as job_serializers
from r3sourcer.apps.hr.tasks import generate_invoice
from r3sourcer.apps.hr.utils import job as job_utils, utils as hr_utils
from r3sourcer.apps.myob.tasks import sync_timesheet


logger = logging.getLogger(__name__)


class BaseTimeSheetViewsetMixin:

    TIME_FORM = {
        'type': constants.CONTAINER_ROW,
        'fields': ('shift_started_at', 'break_started_at', 'break_ended_at', 'shift_ended_at')
    }

    def submit_hours(self, data, time_sheet, is_candidate=True):
        if is_candidate:
            data.update(candidate_submitted_at=timezone.now())
        else:
            data.update(supervisor_approved_at=timezone.now())
        serializer = timesheet_serializers.TimeSheetSerializer(
            time_sheet, data=data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        generate_invoice.delay(time_sheet.id)

        return Response(serializer.data)

    def handle_request(self, request, pk, is_candidate=True, *args, **kwargs):
        time_sheet = get_object_or_404(
            hr_models.TimeSheet.objects.select_for_update(), pk=pk
        )

        if request.method == 'PUT':
            return self.submit_hours(
                kwargs.get('data', request.data), time_sheet, is_candidate
            )

        serializer = timesheet_serializers.TimeSheetSerializer(time_sheet)
        return Response(serializer.data)

    def paginated(self, queryset):  # pragma: no cover
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = timesheet_serializers.TimeSheetSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = timesheet_serializers.TimeSheetSerializer(queryset, many=True)
        return Response(serializer.data)


class TimeSheetViewset(BaseTimeSheetViewsetMixin, BaseApiViewset):

    EVAL_FIELDS = ('was_on_time', 'was_motivated', 'had_ppe_and_tickets', 'met_expectations', 'representation')

    def get_contact(self):
        role_id = self.request.query_params.get('role')

        try:
            role = Role.objects.get(id=role_id)
            contact = role.company_contact_rel.company_contact.contact
        except Exception:
            contact = self.request.user.contact

        return contact

    def get_unapproved_queryset(self, request):
        contact = self.get_contact()
        qs_unapproved = TimesheetFilter.get_filter_for_unapproved(contact)
        queryset = hr_models.TimeSheet.objects.filter(qs_unapproved).distinct()
        return queryset

    def handle_history(self, request):
        if request.user.is_authenticated:
            contact = self.get_contact()
            qs_approved = TimesheetFilter.get_filter_for_approved(contact)
            queryset = hr_models.TimeSheet.objects.filter(qs_approved)
        else:
            queryset = hr_models.TimeSheet.objects.none()

        return self.paginated(queryset)

    @action(methods=['get'], detail=False)
    def unapproved(self, request, *args, **kwargs):  # pragma: no cover
        return self.paginated(self.get_unapproved_queryset(request))

    @transaction.atomic
    @action(methods=['put'], detail=True)
    def approve(self, request, pk, *args, **kwargs):  # pragma: no cover
        return self.handle_request(request, pk, False, data={},
                                   *args, **kwargs)

    @transaction.atomic
    @action(methods=['put'], detail=True)
    def not_agree(self, request, pk, *args, **kwargs):  # pragma: no cover
        data = dict(request.data)
        data.update(candidate_submitted_at=None)
        return self.handle_request(request, pk, False, data=data,
                                   *args, **kwargs)

    @transaction.atomic
    @action(methods=['put'], detail=True)
    def evaluate(self, request, *args, **kwargs):
        timesheet = self.get_object()

        request.data['candidate_contact'] = (
            timesheet.job_offer.candidate_contact.id
        )
        request.data['supervisor'] = timesheet.supervisor.pk
        request.data['reference_timesheet'] = timesheet.pk
        eval_serializer = timesheet_serializers.CandidateEvaluationSerializer(data=request.data)
        eval_serializer.is_valid(raise_exception=True)
        eval_serializer.save()

        return Response({
            'status': 'success',
            'message': _('Candidate evaluated')
        })

    @action(methods=['get'], detail=False)
    def history(self, request, *args, **kwargs):  # pragma: no cover
        return self.handle_history(request)

    @action(methods=['get'], detail=False)
    def approved(self, request, *args, **kwargs):  # pragma: no cover
        return self.handle_history(request)

    @action(methods=['post'], detail=True)
    def confirm(self, request, pk, *args, **kwargs):
        obj = self.get_object()

        obj.going_to_work_confirmation = True
        obj.save(update_fields=['going_to_work_confirmation'])

        return Response({
            'status': 'success'
        })

    @action(methods=['post'], detail=True)
    def resend_sms(self, request, pk, *args, **kwargs):
        obj = self.get_object()

        from r3sourcer.apps.hr.tasks import process_time_sheet_log_and_send_notifications, SHIFT_ENDING
        process_time_sheet_log_and_send_notifications.apply_async(args=[obj.id, SHIFT_ENDING])

        return Response({
            'status': 'success'
        })

    @action(methods=['post'], detail=True)
    def resend_supervisor_sms(self, request, pk, *args, **kwargs):
        obj = self.get_object()

        hr_utils.send_supervisor_timesheet_approve(obj, True)

        return Response({
            'status': 'success'
        })

    @action(methods=['get', 'put'], detail=True)
    def candidate_fill(self, request, pk, *args, **kwargs):
        obj = self.get_object()

        if request.method == 'PUT':
            data = self.prepare_related_data(request.data)
            data['candidate_submitted_at'] = timezone.now()
            serializer = timesheet_serializers.TimeSheetManualSerializer(obj, data=data, partial=True)
            serializer.is_valid(raise_exception=True)

            if serializer.validated_data.get('send_supervisor_message'):
                hr_utils.send_supervisor_timesheet_approve(obj, True)

            time_sheet = serializer.save()
            time_sheet.candidate_submitted_at = timezone.now()
        else:
            serializer = timesheet_serializers.TimeSheetManualSerializer(obj)

        return Response(serializer.data)

    @action(methods=['get', 'put'], detail=True)
    def supervisor_approve(self, request, pk, *args, **kwargs):
        obj = self.get_object()

        if request.method == 'PUT':
            data = self.prepare_related_data(request.data)
            data['supervisor_approved_at'] = timezone.now()
            serializer = timesheet_serializers.TimeSheetManualSerializer(obj, data=data, partial=True)
            serializer.is_valid(raise_exception=True)

            if serializer.validated_data.get('send_supervisor_message'):
                hr_utils.send_supervisor_timesheet_approve(obj, True)

            if serializer.validated_data.get('send_candidate_message'):
                from r3sourcer.apps.hr.tasks import process_time_sheet_log_and_send_notifications, SUPERVISOR_DECLINED
                process_time_sheet_log_and_send_notifications.apply_async(args=[obj.id, SUPERVISOR_DECLINED])

            serializer.save()

            generate_invoice.apply_async([obj.id], countdown=10)
        else:
            if not obj.break_started_at or not obj.break_ended_at:
                obj.no_break = True
            serializer = timesheet_serializers.TimeSheetManualSerializer(obj)

        return Response(serializer.data)

    @action(methods=['post'], detail=True)
    def sync(self, request, pk, *args, **kwargs):
        obj = self.get_object()

        sync_timesheet.delay(obj.id)

        return Response({'status': 'success'})

    @transaction.atomic
    @action(methods=['post'], detail=True)
    def approve_by_pin(self, request, pk, *args, **kwargs):
        """
        Approval action to timesheet.
        Would be used for approving through pin code.
        """

        time_sheet = get_object_or_404(hr_models.TimeSheet.objects.select_for_update(), pk=pk)

        serializer = timesheet_serializers.PinCodeSerializer(instance=time_sheet, data=request.data)
        serializer.is_valid(raise_exception=True)

        # check if already approved
        if time_sheet.supervisor_approved_at:
            return Response({
                "description": _("TimeSheet already confirmed")
            }, status=status.HTTP_400_BAD_REQUEST)

        # approve timesheet
        time_sheet.supervisor_approved_at = timezone.now()
        time_sheet.supervisor_approved_scheme = serializer.APPROVAL_SCHEME
        time_sheet.save()

        logger.debug("TimeSheet {ts_id} approved through pin.".format(ts_id=time_sheet.id))

        return Response(status=status.HTTP_200_OK)

    @transaction.atomic
    @action(methods=['post'], detail=True)
    def approve_by_signature(self, request, pk, *args, **kwargs):
        """
        Approval action to timesheet.
        Would be used for approving through signature.
        """

        time_sheet = get_object_or_404(hr_models.TimeSheet.objects.select_for_update(), pk=pk)

        # check if already approved
        if time_sheet.supervisor_approved_at:
            return Response({
                "description": _("TimeSheet already confirmed")
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = timesheet_serializers.TimeSheetSignatureSerializer(instance=time_sheet, data=request.data)
        serializer.is_valid(raise_exception=True)

        logger.debug("TimeSheet {ts_id} approved through signature.".format(
            ts_id=time_sheet.id
        ))

        # approve timesheet
        serializer.save(
            supervisor_approved_at=timezone.now(),
            supervisor_approved_scheme=serializer.APPROVAL_SCHEME
        )

        return Response(status=status.HTTP_200_OK)


class InvoiceViewset(BaseApiViewset):

    http_method_names = ['get', 'options']

    @action(methods=['get'], detail=True)
    def pdf(self, request, *args, **kwargs):
        invoice = self.get_object()

        try:
            pdf_file_obj = File.objects.get(
                name='invoice_{}_{}.pdf'.format(
                    invoice.number,
                    date_format(invoice.date, 'Y_m_d')
                )
            )

        except Exception:
            pdf_file_obj = payment.InvoiceService.generate_pdf(invoice)

        pdf_url = pdf_file_obj.url

        return Response({
            'status': 'success',
            'pdf': pdf_url,
        })


class JobOfferViewset(BaseApiViewset):

    @action(methods=['get'], detail=False)
    def candidate(self, request, *args, **kwargs):  # pragma: no cover
        return self.list(request, *args, **kwargs)

    @action(methods=['post'], detail=True)
    def accept(self, request, *args, **kwargs):  # pragma: no cover
        obj = self.get_object()
        obj.accept()

        return Response({'status': 'success'})

    @action(methods=['post'], detail=True)
    def cancel(self, request, *args, **kwargs):  # pragma: no cover
        obj = self.get_object()
        obj.cancel()

        return Response({'status': 'success'})

    @action(methods=['post'], detail=True)
    def resend(self, request, *args, **kwargs):  # pragma: no cover
        obj = self.get_object()
        serializer_class = self.get_serializer_class()

        if serializer_class.is_available_for_resend(obj):
            if obj.reply_received_by_sms is None:
                if obj.offer_sent_by_sms is not None:
                    obj.offer_sent_by_sms.no_check_reply()

                if obj.is_cancelled():
                    obj.status = hr_models.JobOffer.STATUS_CHOICES.undefined

            obj.save(initial=True)

        return Response({'status': 'success'})

    @action(methods=['post'], detail=True)
    def send(self, request, *args, **kwargs):  # pragma: no cover
        obj = self.get_object()
        serializer_class = self.get_serializer_class()

        if serializer_class.is_available_for_send(obj):
            obj.status = hr_models.JobOffer.STATUS_CHOICES.undefined
            obj.save(initial=True)

        return Response({'status': 'success'})

    def perform_destroy(self, instance):
        instance.time_sheets.all().delete()
        instance.delete()


class JobViewset(BaseApiViewset):

    @action(methods=['get', 'post'], detail=True)
    def fillin(self, request, *args, **kwargs):
        job = self.get_object()

        requested_shift_ids = request.query_params.getlist('shifts')

        now = timezone.now()
        today = now.date()

        shifts_q = Q(id__in=requested_shift_ids) if requested_shift_ids else Q()

        init_shifts = list(hr_models.Shift.objects.filter(
            shifts_q,
            Q(date__shift_date=today, time__gte=now.timetz()) | Q(date__shift_date__gt=today),
            date__job=job,
            date__cancelled=False,
        ).annotate(
            accepted_jo_count=Sum(Case(
                When(job_offers__status=hr_models.JobOffer.STATUS_CHOICES.accepted, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ))
        ).filter(accepted_jo_count__lt=F('workers')).select_related('date').order_by('date__shift_date', 'time'))

        if request.method == 'POST':
            return self.fillin_post(request, init_shifts)

        if not init_shifts:
            candidate_contacts = candidate_models.CandidateContact.objects.none()
        else:
            candidate_contacts = job_utils.get_available_candidate_list(job)
            is_pool = request.query_params.get('pool', False)

            if is_pool:
                candidate_contacts = candidate_contacts.exclude(
                    candidate_rels__master_company=job.provider_company
                ).distinct()
            else:
                candidate_contacts = candidate_contacts.filter(
                    candidate_rels__master_company=job.provider_company, candidate_rels__active=True
                ).distinct()

            transportation = request.GET.get('transportation_to_work', None)
            if transportation:
                transportation = int(transportation)
                candidate_contacts = candidate_contacts.filter(transportation_to_work=transportation)

        search_term = request.GET.get('q', '')
        if search_term:
            candidate_contacts = self.search_candidate_contacts(candidate_contacts, search_term)

        # do:
        # filter overpriced candidates
        overpriced = request.GET.get('overpriced', 'False') == 'True'
        overpriced_candidates = []
        if job.hourly_rate_default:
            overpriced_qry = Q(
                candidate_skills__skill=job.position,
                candidate_skills__score__gt=0
            )
            hourly_rate = job.hourly_rate_default
            overpriced_candidates = candidate_contacts.filter(
                overpriced_qry,
                candidate_skills__hourly_rate__gt=hourly_rate,
            ).values_list('id', flat=True)

            if not overpriced:
                candidate_contacts = candidate_contacts.filter(
                    overpriced_qry,
                    candidate_skills__hourly_rate__lte=hourly_rate,
                )
        # end

        # do:
        # filter partially available
        partially_available = request.GET.get('available', 'True') == 'True'
        partially_available_candidates = {}
        if init_shifts:
            partially_available_candidates = job_utils.get_partially_available_candidate_ids(
                candidate_contacts, init_shifts
            )

            unavailable_all = [
                partial for partial, shifts in partially_available_candidates.items()
                if len(shifts) == len(init_shifts)
            ]

            candidate_contacts = candidate_contacts.exclude(
                id__in=unavailable_all
            )

            for key in unavailable_all:
                partially_available_candidates.pop(key)

            if not partially_available:
                candidate_contacts = candidate_contacts.exclude(
                    id__in=partially_available_candidates.keys()
                )
            else:
                cache_dates = {}

                def map_dates(vs):
                    if vs.id not in cache_dates:
                        vs_datetime = timezone.make_aware(datetime.datetime.combine(vs.date.shift_date, vs.time))
                        cache_dates[vs.id] = vs_datetime
                    return cache_dates[vs.id]

                for r_id, shifts in partially_available_candidates.items():
                    partially_available_candidates[r_id] = map(
                        map_dates, [shift for shift in init_shifts if shift.id not in shifts]
                    )
        # end

        when_list = self._get_undefined_jo_lookups(init_shifts)

        candidate_contacts = candidate_contacts.annotate(
            jos=Sum(Case(
                *when_list,
                default=Value(0),
                output_field=IntegerField()
            ))
        )

        company_contact = request.user.contact.company_contact.first()
        if company_contact:
            favourite_list = list(candidate_contacts.filter(
                Q(favouritelists__job=job) |
                Q(favouritelists__jobsite=job.jobsite) |
                Q(favouritelists__company=job.customer_company) |
                Q(favouritelists__job__isnull=True,
                  favouritelists__jobsite__isnull=True,
                  favouritelists__company__isnull=True),
                favouritelists__company_contact=company_contact
            ).values_list('id', flat=True).distinct())
        else:
            favourite_list = []

        booked_before_list = list(candidate_contacts.filter(
            job_offers__in=job.get_job_offers().values('id'),
            job_offers__time_sheets__isnull=False
        ).values_list('id', flat=True))

        carrier_list = list(candidate_contacts.filter(
            carrier_lists__confirmed_available=True, carrier_lists__target_date__gte=today
        ).values_list('id', flat=True))

        top_contacts = set(favourite_list + booked_before_list + carrier_list)
        if len(top_contacts) > 0:
            candidate_contacts = candidate_contacts.annotate(
                top_order=Case(
                    *[When(pk=pk, then=0) for pos, pk in enumerate(top_contacts)],
                    default=1,
                    output_field=IntegerField()
                )
            )

        job_tags = job.tags.values_list('tag_id', flat=True)

        candidate_contacts = candidate_contacts.annotate(
            distance_to_jobsite=Case(
                When(contact__distance_caches__jobsite=job.jobsite,
                     then='contact__distance_caches__distance'),
                default=-1
            ),
            time_to_jobsite=Case(
                When(contact__distance_caches__jobsite=job.jobsite,
                     contact__distance_caches__time__isnull=False,
                     then='contact__distance_caches__time'),
                default=-1
            ),
            skills_score=Max(Case(
                When(candidate_skills__score__gt=0,
                     candidate_skills__skill__active=True,
                     then='candidate_skills__score'),
                default=0
            )),
            last_timesheet_date=Max('job_offers__time_sheets__shift_started_at'),
            tags_count=Sum(Case(
                When(tag_rels__tag_id__in=job_tags, job_offers__isnull=True, then=1),
                default=0,
                output_field=IntegerField(),
            ))
        ).prefetch_related('tag_rels__tag')

        tags_filter = request.query_params.get('show_without_tags', None) in ('True', None)
        if not tags_filter:
            candidate_contacts = candidate_contacts.filter(tags_count=len(job_tags))

        restrict_radius = int(request.GET.get('distance_to_jobsite', -1))
        if restrict_radius > -1:
            candidate_contacts = candidate_contacts.filter(distance_to_jobsite__lte=restrict_radius * 1000)

        sort_fields = []
        if len(top_contacts) > 0:
            sort_fields.append('top_order')

        candidate_contacts = self.sort_candidates(request, candidate_contacts, *sort_fields)

        context = {
            'partially_available_candidates': partially_available_candidates,
            'overpriced': overpriced_candidates,
            'job': job,
            'favourite_list': favourite_list,
            'booked_before_list': booked_before_list,
            'carrier_list': carrier_list,
        }

        jobsite_address = job.jobsite.get_address()

        job_ctx = {
            'id': job.id,
            '__str__': str(job),
            'jobsite': str(job.jobsite),
            'position': str(job.position),
            'workers': str(job.workers),
        }
        if jobsite_address:
            job_ctx.update({
                'address': str(jobsite_address),
                'longitude': jobsite_address.longitude,
                'latitude': jobsite_address.latitude,
            })

        serializer = job_serializers.JobFillinSerialzier(
            candidate_contacts[:51], context=context, many=True
        )
        return Response({
            'shifts': [
                dict(
                    date=shift.date.shift_date,
                    **ApiBaseRelatedField.to_read_only_data(shift)
                ) for shift in init_shifts
            ],
            'job': job_ctx,
            'list': serializer.data,
        })

    def fillin_post(self, request, shifts):
        candidate_ids = request.data.get('candidates', []) if isinstance(request.data, dict) else request.data
        fill_shifts = request.data.get('shifts', None) if isinstance(request.data, dict) else None

        if not candidate_ids:
            raise exceptions.ParseError(_('No Candidates has been chosen'))

        for candidate_id in candidate_ids:
            for shift in shifts:
                if fill_shifts and str(shift.id) not in fill_shifts:
                    continue

                unavailable = job_utils.get_partially_available_candidate_ids_for_vs(
                    candidate_models.CandidateContact.objects.filter(id=candidate_id),
                    shift.date.shift_date, shift.time
                )
                if len(unavailable) == 0:
                    hr_models.JobOffer.objects.create(
                        shift=shift,
                        candidate_contact_id=candidate_id,
                    )

        return Response({
            'status': 'ok',
        })

    def _get_undefined_jo_lookups(self, init_shifts):
        when_list = []

        for init_shift in init_shifts:
            shift_start_time = timezone.make_aware(
                datetime.datetime.combine(init_shift.date.shift_date, init_shift.time)
            )

            from_date = shift_start_time - datetime.timedelta(hours=settings.VACANCY_FILLING_TIME_DELTA)
            to_date = shift_start_time + datetime.timedelta(hours=settings.VACANCY_FILLING_TIME_DELTA)

            from_lookup = Q(
                job_offers__shift__date__shift_date=from_date.date(),
                job_offers__shift__time__gte=from_date.timetz()
            ) | Q(job_offers__shift__date__shift_date__gt=from_date.date())

            to_lookup = Q(
                job_offers__shift__date__shift_date=to_date.date(),
                job_offers__shift__time__gte=to_date.timetz()
            ) | Q(job_offers__shift__date__shift_date__gt=to_date.date())

            when_list.append(
                When(
                    from_lookup & to_lookup &
                    Q(job_offers__status=hr_models.JobOffer.STATUS_CHOICES.undefined),
                    then=1
                )
            )

        return when_list

    def search_candidate_contacts(self, candidate_contacts, search_term=''):
        """
        Make search by candidate contact first name, last name and title
        :param candidate_contacts:
        :param search_term: search parameter
        :return:
        """
        search_fields = ['contact__first_name', 'contact__last_name', 'contact__title']
        orm_lookups = ["%s__icontains" % search_field for search_field in search_fields]

        for bit in search_term.split():
            or_queries = [Q(**{orm_lookup: bit}) for orm_lookup in orm_lookups]
            candidate_contacts = candidate_contacts.filter(reduce(operator.or_, or_queries))
        return candidate_contacts

    def sort_candidates(self, request, candidate_contacts, *fields):
        params = request.query_params.get(api_settings.ORDERING_PARAM)
        fields = list(fields)
        fields.append('-tags_count')

        if params:
            fields = fields.extend([param.strip() for param in params.split(',')] if params else [])

        return candidate_contacts.order_by(*fields)

    @action(methods=['get', 'put'], detail=True)
    def extend(self, request, *args, **kwargs):
        job = self.get_object()

        if request.method == 'PUT':
            is_autofill = request.data.get('autofill', False)
            try:
                latest_shift_date = job.shift_dates.filter(cancelled=False, shifts__isnull=False).latest('shift_date')
            except hr_models.ShiftDate.DoesNotExist:
                raise exceptions.NotFound(_('Latest Shift Date not found'))

            new_shift_dates = request.data.get('job_shift', [])
            new_shift_dates_objs = []

            for new_shift_date in new_shift_dates:
                new_shift_date = datetime.datetime.strptime(new_shift_date, '%Y-%m-%d').date()
                new_shift_date_obj, created = hr_models.ShiftDate.objects.get_or_create(
                    job=job, shift_date=new_shift_date, defaults={
                        'workers': latest_shift_date.workers,
                        'hourly_rate': latest_shift_date.hourly_rate,
                    },
                )
                new_shift_dates_objs.append(new_shift_date_obj)

            if is_autofill:
                shift_objs = hr_models.JobOffer.objects.filter(shift__date=latest_shift_date)
            else:
                shift_objs = hr_models.Shift.objects.filter(date=latest_shift_date)

            for new_shift_date_obj in new_shift_dates_objs:
                self._extend_shift_date(job, new_shift_date_obj, shift_objs, is_autofill)

            serializer = job_serializers.JobExtendSerialzier(job)
        else:
            serializer = job_serializers.JobExtendSerialzier(job)

        return Response(serializer.data)

    def _extend_shift_date(self, job, new_shift_date, shifts, is_autofill):
        for shift in shifts:
            shift_obj = shift.shift if is_autofill else shift
            new_shift_obj, created = hr_models.Shift.objects.get_or_create(
                date=new_shift_date, time=shift_obj.time, defaults={
                    'workers': shift_obj.workers,
                    'hourly_rate': shift_obj.hourly_rate,
                },
            )

            if is_autofill:
                hr_models.JobOffer.objects.create(
                    shift=new_shift_obj,
                    candidate_contact=shift.candidate_contact,
                )


class TimeSheetCandidateViewset(
    BaseTimeSheetViewsetMixin,
    BaseViewsetMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    def get_candidate_queryset(self, request):
        contact = request.user.contact

        qs_approved = TimesheetFilter.get_filter_for_approved(request.user.contact)
        qs_unapproved = TimesheetFilter.get_filter_for_unapproved(request.user.contact)

        queryset = hr_models.TimeSheet.objects.filter(
            job_offer__candidate_contact_id=contact.candidate_contacts.id
        ).annotate(
            approved=Case(When(qs_approved, then=True),
                          When(qs_unapproved, then=False),
                          output_field=BooleanField(), default=False)
        ).order_by('approved', 'shift_started_at')

        return queryset

    def list(self, request, *args, **kwargs):
        return self.paginated(self.get_candidate_queryset(request))

    @transaction.atomic
    @action(methods=['get', 'put'], detail=True)
    def submit(self, request, pk, *args, **kwargs):  # pragma: no cover
        return self.handle_request(request, pk, *args, **kwargs)


class JobOffersCandidateViewset(
    BaseViewsetMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    def get_queryset(self):
        contact = self.request.user.contact
        return super().get_queryset().filter(
            candidate_contact__contact=contact
        )


class ShiftViewset(BaseApiViewset):

    def perform_destroy(self, instance):
        shift_date = instance.date
        instance.delete()

        if not shift_date.shifts.exists():
            shift_date.delete()


class JobsiteViewset(GoogleAddressMixin, BaseApiViewset):

    @action(methods=['get'], detail=False)
    def jobsite_map(self, request, *args, **kwargs):
        serializer = job_serializers.JobsiteMapFilterSerializer(data=self.request.query_params)
        serializer.is_valid()
        if not serializer.validated_data:
            return Response([])

        filter_qry = Q(jobsites__isnull=False) | Q(company_addresses__isnull=False)

        filter_by = serializer.validated_data.get('filter_by')
        if filter_by:
            if filter_by == 'clients':
                filter_qry = Q(company_addresses__isnull=False)
            elif filter_by == 'jobsites':
                filter_qry = Q(jobsites__isnull=False)
            elif filter_by == 'only_hqs':
                filter_qry = Q(company_addresses__isnull=False, company_addresses__hq=True)

        filter_client = serializer.validated_data.get('client')
        if filter_client:
            filter_qry = Q(company_addresses__company_id=filter_client)

        filter_jobsite = serializer.validated_data.get('jobsite')
        if filter_jobsite:
            filter_qry = Q(jobsites__id=filter_jobsite)

        filter_manager = serializer.validated_data.get('portfolio_manager')
        if filter_manager:
            filter_qry = (
                Q(company_addresses__primary_contact_id=filter_manager) |
                Q(jobsites__primary_contact_id=filter_manager)
            )

        jobsite_data = Address.objects.filter(filter_qry).exclude(
            latitude=decimal.Decimal('0.0'),
            longitude=decimal.Decimal('0.0'),
        ).annotate(
            name=F('jobsites__short_name'),
            first_name=F('jobsites__primary_contact__contact__first_name'),
            last_name=F('jobsites__primary_contact__contact__last_name'),
            title=F('jobsites__primary_contact__contact__title'),
            job_title=F('jobsites__primary_contact__job_title'),
            phone_mobile=F('jobsites__primary_contact__contact__phone_mobile'),
            jobsite_id=F('jobsites__id'),
            client_first_name=F('company_addresses__primary_contact__contact__first_name'),
            client_last_name=F('company_addresses__primary_contact__contact__last_name'),
            client_title=F('company_addresses__primary_contact__contact__title'),
            client_job_title=F('company_addresses__primary_contact__job_title'),
            client_name=F('company_addresses__company__name'),
            client_phone_mobile=F('company_addresses__primary_contact__contact__phone_mobile'),
            client_hq=F('company_addresses__hq'),
        ).prefetch_related()

        serializer = job_serializers.JobsiteMapAddressSerializer(jobsite_data, many=True)

        return Response(serializer.data)
