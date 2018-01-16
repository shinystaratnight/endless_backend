import datetime

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q, Case, When, BooleanField, Value, IntegerField, Count, F, Sum
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import ugettext_lazy as _
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from filer.models import File

from r3sourcer.apps.candidate import models as candidate_models
from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.core.api.viewsets import BaseApiViewset
from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.core.api.decorators import detail_route, list_route
from r3sourcer.apps.core.models.constants import CANDIDATE
from r3sourcer.apps.core.utils.text import format_lazy
from r3sourcer.apps.core_adapter import constants
from r3sourcer.apps.core_adapter.utils import api_reverse_lazy
from r3sourcer.apps.hr import models as hr_models, payment
from r3sourcer.apps.hr.api.filters import TimesheetFilter
from r3sourcer.apps.hr.api.serializers import timesheet as timesheet_serializers, vacancy as vacancy_serializers
from r3sourcer.apps.hr.utils.vacancy import get_partially_available_candidate_ids


class ExtranetTimesheetEndpoint(ApiEndpoint):

    model = hr_models.TimeSheet
    serializer = timesheet_serializers.TimeSheetSerializer

    list_buttons = []


class ExtranetCandidateTimesheetEndpoint(ApiEndpoint):

    model = hr_models.TimeSheet
    serializer = timesheet_serializers.TimeSheetSerializer

    list_buttons = []

    def get_list_filter(self):
        return [{
            'field': 'shift_started_at',
            'type': constants.FIELD_DATE,
        }, {
            'type': constants.FIELD_SELECT,
            'field': 'approved',
            'label': _('Status'),
            'choices': [{'label': 'Approved', 'value': 'True'},
                        {'label': 'Unapproved', 'value': 'False'}]
        }]


class VacancyFillinEndpoint(ApiEndpoint):

    model = candidate_models.CandidateContact
    serializer = vacancy_serializers.VacancyFillinSerialzier

    list_buttons = []

    highlight = {
        'field': 'color',
        'values': {
            1: 'lightgreen',
            2: '#dcdcdc',
            3: 'red',
            4: '#ff7f00',
            5: '#ff7f50',
        },
    }


class TimeSheetViewset(BaseApiViewset):

    TIME_FORM = {
        'type': constants.CONTAINER_ROW,
        'fields': ('shift_started_at', 'break_started_at',
                   'break_ended_at', 'shift_ended_at')
    }

    EVAL_FIELDS = ('was_on_time', 'was_motivated', 'had_ppe_and_tickets',
                   'met_expectations', 'representation')

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

        return Response(serializer.data)

    def get_unapproved_queryset(self, request):
        qs_unapproved = TimesheetFilter.get_filter_for_unapproved(request.user.contact)
        queryset = hr_models.TimeSheet.objects.filter(qs_unapproved).distinct()
        return queryset

    def get_candidate_queryset(self, request):
        contact = request.user.contact
        role = contact.get_role()

        qs_approved = TimesheetFilter.get_filter_for_approved(request.user.contact)
        qs_unapproved = TimesheetFilter.get_filter_for_unapproved(request.user.contact)

        queryset = hr_models.TimeSheet.objects.annotate(
            approved=Case(When(qs_approved, then=True),
                          When(qs_unapproved, then=False),
                          output_field=BooleanField(), default=False)
        ).order_by('approved')

        if role == CANDIDATE:
            queryset = queryset.filter(vacancy_offer__candidate_contact_id=contact.candidate_contacts.id)
        return queryset

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

    def handle_history(self, request):
        qs_approved = TimesheetFilter.get_filter_for_approved(request.user.contact)
        queryset = hr_models.TimeSheet.objects.filter(qs_approved)

        return self.paginated(queryset)

    @transaction.atomic
    @detail_route(
        methods=['GET', 'PUT'],
        serializer=timesheet_serializers.TimeSheetSerializer,
        fieldsets=({
            'type': constants.CONTAINER_ROW,
            'fields': ({
                'type': constants.FIELD_STATIC,
                'field': 'supervisor',
            }, {
                'type': constants.FIELD_STATIC,
                'field': 'company',
                'label': _('Company'),
            }, {
                'type': constants.FIELD_STATIC,
                'field': 'jobsite',
                'label': _('Jobsite'),
            }, {
                'type': constants.FIELD_STATIC,
                'field': 'position',
                'label': _('Position'),
            })
        }, TIME_FORM)
    )
    def submit(self, request, pk, *args, **kwargs):  # pragma: no cover
        return self.handle_request(request, pk, *args, **kwargs)

    @list_route(
        methods=['GET'],
        endpoint=ExtranetTimesheetEndpoint(),
        list_display=[{
            'field': 'vacancy_offer.candidate_contact.contact.picture',
            'type': constants.FIELD_PICTURE,
        }, {
            'label': _('Position'),
            'fields': ({
                'type': constants.FIELD_LINK,
                'endpoint': format_lazy(
                    '{}{{vacancy_offer.candidate_contact.id}}/',
                    api_reverse_lazy('candidate/candidatecontacts')
                ),
                'action': 'showCandidateProfile',
                'field': 'vacancy_offer.candidate_contact',
            }, 'position'),
        }, {
            'label': _('Times'),
            'fields': ({
                'type': constants.FIELD_STATIC,
                'text': format_lazy('{{shift_started_at__date}}'),
                'label': _('Shift date'),
                'field': 'shift_started_at',
            }, {
                'type': constants.FIELD_STATIC,
                'text': format_lazy('{{shift_started_at__time}}'),
                'label': _('Shift started at'),
                'field': 'shift_started_at',
            }, {
                'type': constants.FIELD_STATIC,
                'text': format_lazy(
                    '{{break_started_at__time}} - {{break_ended_at__time}}'),
                'label': _('Break'),
                'field': 'break_started_at',
            }, {
                'type': constants.FIELD_STATIC,
                'text': format_lazy('{{shift_started_at__time}}'),
                'label': _('Shift ended at'),
                'field': 'shift_ended_at',
            }),
        }, {
            'type': constants.FIELD_BUTTON,
            'icon': 'fa-check',
            'label': _('Approve'),
            'text': _('Approve'),
            'color': 'success',
            'action': 'approveTimesheet',
            'field': 'id',
            'hidden': 'supervisor_approved_at',
            'replace_by': 'supervisor',
            'endpoint': format_lazy(
                '{}{{id}}/approve/', api_reverse_lazy('hr/timesheets')
            ),
        }, {
            'type': constants.FIELD_BUTTON,
            'icon': 'fa-pencil',
            'label': _('Change'),
            'text': _('Change'),
            'color': 'danger',
            'action': 'changeTimesheet',
            'field': 'id',
            'hidden': 'supervisor_approved_at',
            'endpoint': format_lazy(
                '{}{{id}}/not_agree/',
                api_reverse_lazy('hr/timesheets')
            ),
        }, {
            'type': constants.FIELD_BUTTON,
            'icon': 'fa-star',
            'repeat': 5,
            'label': _('Evaluate'),
            'color': 'warning',
            'action': 'evaluateCandidate',
            'field': 'id',
            'endpoint': format_lazy(
                '{}{{id}}/evaluate/',
                api_reverse_lazy('hr/timesheets')
            ),
        }]
    )
    def unapproved(self, request, *args, **kwargs):  # pragma: no cover
        return self.paginated(self.get_unapproved_queryset(request))

    @list_route(
        methods=['GET'],
        endpoint=ExtranetCandidateTimesheetEndpoint(),
        list_display=[{
            'field': 'vacancy_offer.candidate_contact.contact.picture',
            'type': constants.FIELD_PICTURE,
        }, {
            'label': _('Position'),
            'fields': ({
                'type': constants.FIELD_LINK,
                'endpoint': format_lazy(
                    '{}{{vacancy_offer.candidate_contact.id}}/',
                    api_reverse_lazy('candidate/candidatecontacts')
                ),
                'action': 'showCandidateProfile',
                'field': 'vacancy_offer.candidate_contact',
            }, 'position'),
        }, {
            'label': _('Times'),
            'fields': ({
                'type': constants.FIELD_STATIC,
                'text': format_lazy('{{shift_started_at__date}}'),
                'label': _('Shift date'),
                'field': 'shift_started_at',
            }, {
                'type': constants.FIELD_STATIC,
                'text': format_lazy('{{shift_started_at__time}}'),
                'label': _('Shift started at'),
                'field': 'shift_started_at',
            }, {
                'type': constants.FIELD_STATIC,
                'text': format_lazy(
                    '{{break_started_at__time}} - {{break_ended_at__time}}'),
                'label': _('Break'),
                'field': 'break_started_at',
            }, {
                'type': constants.FIELD_STATIC,
                'text': format_lazy('{{shift_started_at__time}}'),
                'label': _('Shift ended at'),
                'field': 'shift_ended_at',
            }),
        }, {
            'type': constants.FIELD_BUTTON,
            'icon': 'fa-check',
            'label': _('Approve'),
            'text': _('Approve'),
            'color': 'success',
            'action': 'approveTimesheet',
            'field': 'id',
            'hidden': 'supervisor_approved_at',
            'replace_by': 'supervisor',
            'endpoint': format_lazy(
                '{}{{id}}/approve/', api_reverse_lazy('hr/timesheets')
            ),
        }, {
            'type': constants.FIELD_BUTTON,
            'icon': 'fa-pencil',
            'label': _('Change'),
            'text': _('Change'),
            'color': 'danger',
            'action': 'changeTimesheet',
            'field': 'id',
            'hidden': 'supervisor_approved_at',
            'endpoint': format_lazy(
                '{}{{id}}/not_agree/',
                api_reverse_lazy('hr/timesheets')
            ),
        }, {
            'type': constants.FIELD_BUTTON,
            'icon': 'fa-star',
            'repeat': 5,
            'label': _('Evaluate'),
            'color': 'warning',
            'action': 'evaluateCandidate',
            'field': 'id',
            'endpoint': format_lazy(
                '{}{{id}}/evaluate/',
                api_reverse_lazy('hr/timesheets')
            ),
        }, {
            'label': _('Jobsite'),
            'fields': ('jobsite', 'supervisor')
        }, {
            'label': _('Going to work'),
            'field': 'going_to_work_confirmation',
            'type': constants.FIELD_ICON,
        }, {
            'label': _('Signed by'),
            'fields': ('supervisor', 'supervisor_approved_at')
        }]
    )
    def candidate(self, request, *args, **kwargs):
        return self.paginated(self.get_candidate_queryset(request))

    @transaction.atomic
    @detail_route(methods=['PUT'])
    def approve(self, request, pk, *args, **kwargs):  # pragma: no cover
        return self.handle_request(request, pk, False, data={},
                                   *args, **kwargs)

    @transaction.atomic
    @detail_route(
        methods=['PUT'],
        serializer=timesheet_serializers.TimeSheetSerializer,
        fieldsets=(TIME_FORM, )
    )
    def not_agree(self, request, pk, *args, **kwargs):  # pragma: no cover
        data = dict(request.data)
        data.update(candidate_submitted_at=None)
        return self.handle_request(request, pk, False, data=data,
                                   *args, **kwargs)

    @transaction.atomic
    @detail_route(
        methods=['PUT'],
        serializer=timesheet_serializers.CandidateEvaluationSerializer,
        fieldsets=(*[{
            'field': field,
            'type': constants.FIELD_ICON,
            'values': {
                True: 'star',
                False: 'star-o',
            },
            'color': 'warning',
            'default': True,
        } for field in EVAL_FIELDS], 'level_of_communication')
    )
    def evaluate(self, request, *args, **kwargs):
        timesheet = self.get_object()

        request.data['candidate_contact'] = (
            timesheet.vacancy_offer.candidate_contact.id
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

    @list_route(
        methods=['GET'],
        endpoint=ExtranetTimesheetEndpoint(),
        list_display=[{
            'label': _('Times'),
            'fields': ({
                'type': constants.FIELD_STATIC,
                'text': format_lazy('{{shift_started_at__date}}'),
                'label': _('Shift date'),
                'field': 'shift_started_at',
            }, {
                'type': constants.FIELD_STATIC,
                'text': format_lazy('{{shift_started_at__time}}'),
                'label': _('Shift started at'),
                'field': 'shift_started_at',
            }, {
                'type': constants.FIELD_STATIC,
                'text': format_lazy(
                    '{{break_started_at__time}} - {{break_ended_at__time}}'),
                'label': _('Break'),
                'field': 'break_started_at',
            }, {
                'type': constants.FIELD_STATIC,
                'text': format_lazy('{{shift_started_at__time}}'),
                'label': _('Shift ended at'),
                'field': 'shift_ended_at',
            }),
        }, {
            'label': _('Jobsite'),
            'fields': ('jobsite', 'supervisor')
        }, {
            'label': _('Going to work'),
            'field': 'going_to_work_confirmation',
            'type': constants.FIELD_ICON,
        }, {
            'label': _('Signed by'),
            'fields': ('supervisor', 'supervisor_approved_at')
        }]
    )
    def history(self, request, *args, **kwargs):  # pragma: no cover
        return self.handle_history(request)

    @list_route(
        methods=['GET'],
        endpoint=ExtranetTimesheetEndpoint(),
        list_display=[{
            'field': 'vacancy_offer.candidate_contact.contact.picture',
            'type': constants.FIELD_PICTURE,
        }, {
            'label': _('Position'),
            'fields': ({
                'type': constants.FIELD_LINK,
                'endpoint': format_lazy(
                    '{}{{vacancy_offer.candidate_contact.id}}/',
                    api_reverse_lazy('candidate/candidatecontacts')
                ),
                'action': 'showCandidateProfile',
                'field': 'vacancy_offer.candidate_contact',
            }, 'position'),
        }, {
            'label': _('Times'),
            'fields': ({
                'type': constants.FIELD_STATIC,
                'text': format_lazy('{{shift_started_at__date}}'),
                'label': _('Shift date'),
                'field': 'shift_started_at',
            }, {
                'type': constants.FIELD_STATIC,
                'text': format_lazy('{{shift_started_at__time}}'),
                'label': _('Shift started at'),
                'field': 'shift_started_at',
            }, {
                'type': constants.FIELD_STATIC,
                'text': format_lazy(
                    '{{break_started_at__time}} - {{break_ended_at__time}}'),
                'label': _('Break'),
                'field': 'break_started_at',
            }, {
                'type': constants.FIELD_STATIC,
                'text': format_lazy('{{shift_started_at__time}}'),
                'label': _('Shift ended at'),
                'field': 'shift_ended_at',
            }),
        }, {
            'type': constants.FIELD_BUTTON,
            'icon': 'fa-star',
            'repeat': 5,
            'label': _('Evaluate'),
            'color': 'warning',
            'action': 'evaluateCandidate',
            'field': 'id',
            'endpoint': format_lazy(
                '{}{{id}}/evaluate/',
                api_reverse_lazy('hr/timesheets')
            ),
        }]
    )
    def approved(self, request, *args, **kwargs):  # pragma: no cover
        return self.handle_history(request)


class InvoiceViewset(BaseApiViewset):

    http_method_names = ['get', 'options']

    @detail_route(methods=['get'])
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


class VacancyOfferViewset(BaseApiViewset):
    @list_route(
        methods=['GET'],
        list_editable=[{
            'label': _('Shift date and time'),
            'fields': ('shift.date.shift_date', 'shift.time')
        }, 'status']
    )
    def candidate(self, request, *args, **kwargs):  # pragma: no cover
        return self.list(request, *args, **kwargs)

    @detail_route(methods=['POST'])
    def accept(self, request, *args, **kwargs):  # pragma: no cover
        obj = self.get_object()
        obj.status = hr_models.VacancyOffer.STATUS_CHOICES.accepted
        obj.save()

        return Response({'status': 'success'})

    @detail_route(methods=['POST'])
    def cancel(self, request, *args, **kwargs):  # pragma: no cover
        obj = self.get_object()
        obj.cancel()

        return Response({'status': 'success'})

    @detail_route(methods=['POST'])
    def resend(self, request, *args, **kwargs):  # pragma: no cover
        obj = self.get_object()
        serializer_class = self.get_serializer_class()

        if serializer_class.is_available_for_resend(obj):
            if obj.reply_received_by_sms is None:
                if obj.offer_sent_by_sms is not None:
                    obj.offer_sent_by_sms.no_check_reply()
                obj.cancel()

            hr_models.VacancyOffer.objects.create(
                shift=obj.shift,
                candidate_contact=obj.candidate_contact,
            )

        return Response({'status': 'success'})


class VacancyViewset(BaseApiViewset):

    @detail_route(
        methods=['GET', 'POST'],
        endpoint=VacancyFillinEndpoint(),
        list_display=[
            'contact.__str__', 'recruitment_agent', 'available', 'days_from_last_timesheet',
            {
                'type': constants.FIELD_STATIC,
                'field': 'distance_to_jobsite',
                'async': True,
                'endpoint': '/',
                'method': 'post',
                'query': {
                    'candidates': '{id}'
                },
                'request_field': 'distance',
            }, {
                'type': constants.FIELD_STATIC,
                'field': 'time_to_jobsite',
                'async': True,
                'endpoint': '/',
                'method': 'post',
                'query': {
                    'candidates': '{id}'
                },
                'request_field': 'time',
            }, 'skills_score', 'tag_rels', 'count_timesheets',
            'contact.gender', 'nationality', {
                'field': 'transportation_to_work',
                'type': constants.FIELD_SELECT,
            },
            'average_score', 'candidate_scores.reliability', 'strength', 'language', {
                'field': 'hourly_rate',
                'type': constants.FIELD_STATIC,
                'display': '${field}/h',
            },
            'evaluation'
        ]
    )
    def fillin(self, request, *args, **kwargs):
        vacancy = self.get_object()

        now = timezone.now()
        today = now.date()
        init_shifts = list(hr_models.Shift.objects.filter(
            Q(date__shift_date=today, time__gte=now.timetz()) | Q(date__shift_date__gt=today),
            date__vacancy=vacancy,
            date__cancelled=False,
        ).annotate(
            accepted_vo_count=Count(Case(
                When(vacancy_offers__status=hr_models.VacancyOffer.STATUS_CHOICES.accepted, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ))
        ).filter(accepted_vo_count__lt=F('workers')).select_related('date').order_by('date__shift_date', 'time'))

        if not init_shifts:
            candidate_contacts = candidate_models.CandidateContact.objects.none()
        else:
            candidate_contacts = self.get_available_candidate_list(vacancy)

        # TODO: hm...
        # search_term = ''
        # if request.GET.get('q', ''):
        #     search_term = request.GET.get('q', '')
        #     candidate_contacts = self.search_candidate_contacts(candidate_contacts, search_term)

        # do:
        # filter overpriced candidates
        overpriced = request.GET.get('overpriced', None)
        overpriced_candidates = []
        if vacancy.hourly_rate_default:
            overpriced_qry = Q(
                candidate_skills__candidate_skill_rates__valid_from__lte=today,
                candidate_skills__candidate_skill_rates__valid_until__gte=today,
                candidate_skills__skill=vacancy.position,
                candidate_skills__score__gt=0
            )
            hourly_rate = vacancy.hourly_rate_default.hourly_rate
            overpriced_candidates = candidate_contacts.filter(
                overpriced_qry,
                candidate_skills__candidate_skill_rates__hourly_rate__hourly_rate__gt=hourly_rate,
            ).values_list('id', flat=True)

            if not overpriced:
                candidate_contacts = candidate_contacts.filter(
                    overpriced_qry,
                    candidate_skills__candidate_skill_rates__hourly_rate__hourly_rate__lte=hourly_rate,
                )
        # end

        # do:
        # filter partially available
        partially_available = request.GET.get('partially', None)
        partially_available_candidates = {}
        if init_shifts:
            partially_available_candidates = get_partially_available_candidate_ids(candidate_contacts, init_shifts)

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
                    partially_available_candidates[r_id] = map(map_dates, init_shifts.exclude(id__in=shifts))
        # end

        when_list = self._get_undefined_vo_lookups(init_shifts)

        candidate_contacts = candidate_contacts.annotate(
            vos=Sum(Case(
                *when_list,
                default=Value(0),
                output_field=IntegerField()
            ))
        )

        company_contact = request.user.contact.company_contact.first()
        if company_contact:
            favourite_list = list(candidate_contacts.filter(
                Q(favouritelists__vacancy=vacancy) |
                Q(favouritelists__jobsite=vacancy.jobsite) |
                Q(favouritelists__company=vacancy.customer_company) |
                Q(favouritelists__vacancy__isnull=True,
                  favouritelists__jobsite__isnull=True,
                  favouritelists__company__isnull=True),
                favouritelists__company_contact=company_contact
            ).values_list('id', flat=True).distinct())
        else:
            favourite_list = []

        booked_before_list = list(candidate_contacts.filter(
            vacancy_offers__in=vacancy.get_vacancy_offers().values('id'),
            vacancy_offers__time_sheets__isnull=False
        ).values_list('id', flat=True))

        carrier_list = list(candidate_contacts.filter(
            carrier_lists__confirmed_available=True, carrier_lists__target_date__gte=today
        ).values_list('id', flat=True))

        top_contacts = set(favourite_list + booked_before_list + carrier_list)
        if len(top_contacts) > 0:
            preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(top_contacts)])
            candidate_contacts = candidate_contacts.order_by(preserved)

        candidate_contacts = candidate_contacts.prefetch_related('tag_rels__tag')

        # TODO: add restrict by radius
        # restrict_radius = int(request.GET.get('restrict_radius', -1))
        # if restrict_radius > -1:
        #     full_contact_info = [contact for contact in full_contact_info
        #                          if contact['distance_to_jobsite'] > -1
        #                          and contact['distance_to_jobsite'] <= restrict_radius]

        transportation = request.GET.get('transportation', None)
        if transportation:
            transportation = int(transportation)
            candidate_contacts = candidate_contacts.filter(transportation_to_work=transportation)

        # TODO: add sorting
        # order = request.GET.get('order', 'distance_to_jobsite')
        # full_contact_info = self.order_contact_info(full_contact_info, order)
        # candidate_contacts = candidate_contacts.annotate(
        #     order=Case(
        #         When(id__in=favourite_list, then=Value(3)),
        #         When(id__in=booked_before_list + carrier_list, then=Value(1)),
        #         default=Value(0),
        #         output_field=IntegerField()
        #     )
        # ).order_by('-order')

        context = {
            'partially_available_candidates': partially_available_candidates,
            'overpriced': overpriced_candidates,
            'vacancy': vacancy,
            'favourite_list': favourite_list,
            'booked_before_list': booked_before_list,
            'carrier_list': carrier_list,
        }

        jobsite_address = vacancy.jobsite.get_address()

        vacacy_ctx = {
            'id': vacancy.id,
            '__str__': str(vacancy),
        }
        if jobsite_address:
            vacacy_ctx.update({
                'address': str(jobsite_address),
                'longitude': jobsite_address.longitude,
                'latitude': jobsite_address.latitude,
            })

        serializer = vacancy_serializers.VacancyFillinSerialzier(
            candidate_contacts, context=context, many=True
        )
        return Response({
            'vacancy': vacacy_ctx,
            'list': serializer.data,
        })

    def get_available_candidate_list(self, vacancy):
        """
        Gets the list of available candidate contacts for the vacancy fillin form
        :param vacancy: vacancy object
        :return: queryset of the candidate contacts
        """
        today = datetime.date.today()

        content_type = ContentType.objects.get_for_model(candidate_models.CandidateContact)
        objects = core_models.WorkflowObject.objects.filter(
            state__number=70,
            state__workflow__model=content_type,
            active=True,
        ).distinct('object_id').values_list('object_id', flat=True)

        candidate_contacts = candidate_models.CandidateContact.objects.filter(
            contact__is_available=True,
            candidate_skills__skill=vacancy.position,
            candidate_skills__candidate_skill_rates__valid_from__lte=today,
            candidate_skills__candidate_skill_rates__valid_until__gte=today,
            candidate_skills__skill__active=True,
            candidate_skills__score__gt=0,
            id__in=objects
        ).distinct()

        if candidate_contacts.exists():
            blacklists_candidates = hr_models.BlackList.objects.filter(
                Q(jobsite=vacancy.jobsite) | Q(company_contact=vacancy.jobsite.primary_contact),
                candidate_contact__in=candidate_contacts
            ).values_list('candidate_contact', flat=True)

            candidate_contacts = candidate_contacts.exclude(id__in=blacklists_candidates)

            if vacancy.transportation_to_work:
                candidate_contacts = candidate_contacts.filter(transportation_to_work=vacancy.transportation_to_work)

        return candidate_contacts

    def _get_undefined_vo_lookups(self, init_shifts):
        when_list = []

        for init_shift in init_shifts:
            shift_start_time = timezone.make_aware(
                datetime.datetime.combine(init_shift.date.shift_date, init_shift.time)
            )

            from_date = shift_start_time - datetime.timedelta(hours=settings.VACANCY_FILLING_TIME_DELTA)
            to_date = shift_start_time + datetime.timedelta(hours=settings.VACANCY_FILLING_TIME_DELTA)

            from_lookup = Q(
                vacancy_offers__shift__date__shift_date=from_date.date(),
                vacancy_offers__shift__time__gte=from_date.timetz()
            ) | Q(vacancy_offers__shift__date__shift_date__gt=from_date.date())

            to_lookup = Q(
                vacancy_offers__shift__date__shift_date=to_date.date(),
                vacancy_offers__shift__time__gte=to_date.timetz()
            ) | Q(vacancy_offers__shift__date__shift_date__gt=to_date.date())

            when_list.append(
                When(
                    from_lookup & to_lookup &
                    Q(vacancy_offers__status=hr_models.VacancyOffer.STATUS_CHOICES.undefined),
                    then=1
                )
            )

        return when_list
