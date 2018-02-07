import datetime
import operator

from functools import reduce

from django.conf import settings
from django.db import transaction
from django.db.models import Q, Case, When, BooleanField, Value, IntegerField, F, Sum, Max
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import ugettext_lazy as _
from rest_framework import exceptions
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.settings import api_settings
from filer.models import File

from r3sourcer.apps.candidate import models as candidate_models
from r3sourcer.apps.core.api.decorators import detail_route, list_route
from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.core.api.fields import ApiBaseRelatedField
from r3sourcer.apps.core.api.viewsets import BaseApiViewset
from r3sourcer.apps.core.models.constants import CANDIDATE
from r3sourcer.apps.core.utils.text import format_lazy
from r3sourcer.apps.core_adapter import constants
from r3sourcer.apps.core_adapter.utils import api_reverse_lazy
from r3sourcer.apps.hr import models as hr_models, payment
from r3sourcer.apps.hr.api.filters import TimesheetFilter
from r3sourcer.apps.hr.api.serializers import timesheet as timesheet_serializers, vacancy as vacancy_serializers
from r3sourcer.apps.hr.utils import vacancy as vacancy_utils


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

    list_buttons = [{
        'label': _('Show map'),
        'action': 'openMap'
    }]

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

    search_fields = ('contact__first_name', 'contact__last_name')

    list_filter = [{
        'field': 'transportation_to_work',
        'type': constants.FIELD_SELECT,
    }, {
        'field': 'available',
        'label': _('Available'),
        'type': constants.FIELD_SELECT,
        'default': 'True',
        'choices': [
            {'label': _('Partially'), 'value': 'True'},
            {'label': _('All dates'), 'value': 'False'}
        ]
    }, {
        'field': 'overpriced',
        'label': _('Overpriced'),
        'type': constants.FIELD_SELECT,
        'default': 'False',
        'choices': [
            {'label': _('All candidates'), 'value': 'True'},
            {'label': _('Without overpriced'), 'value': 'False'}
        ]
    }, {
        'field': 'distance_to_jobsite',
        'label': _('Distance'),
        'type': constants.FIELD_TEXT,
        'default': 50,
        'min': 0,
        'max': 200,
    }, {
        'type': constants.FIELD_SELECT_MULTIPLE,
        'field': 'date',
        'label': _('Shifts'),
        'query': {
            'shifts': '{id}',
        },
        'data': 'shifts',
        'display': '__str__'
    }]

    ordering_mapping = {
        'distance_to_jobsite': 'distance_to_jobsite',
        'time_to_jobsite': 'time_to_jobsite',
        'candidate_scores.average_score': 'candidate_scores__average_score',
        'skills_score': 'skills_score',
    }

    ordering = ('distance_to_jobsite')


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
        if request.user.is_authenticated:
            qs_approved = TimesheetFilter.get_filter_for_approved(request.user.contact)
            queryset = hr_models.TimeSheet.objects.filter(qs_approved)
        else:
            queryset = hr_models.TimeSheet.objects.none()

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
                'endpoint': reverse_lazy('get_candidate_distance', kwargs={'version': 'v2'}),
                'method': 'post',
                'query': {
                    'candidates': '{id}'
                },
                'request_field': 'distance',
            }, {
                'type': constants.FIELD_STATIC,
                'field': 'time_to_jobsite',
                'async': True,
                'endpoint': reverse_lazy('get_candidate_distance', kwargs={'version': 'v2'}),
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
            'candidate_scores.reliability', 'candidate_scores.average_score', 'strength', 'language', {
                'field': 'hourly_rate',
                'type': constants.FIELD_STATIC,
                'display': '${field}/h',
            },
            'evaluation'
        ]
    )
    def fillin(self, request, *args, **kwargs):
        vacancy = self.get_object()

        requested_shift_ids = request.query_params.getlist('shifts')

        now = timezone.now()
        today = now.date()

        shifts_q = Q(id__in=requested_shift_ids) if requested_shift_ids else Q()

        init_shifts = list(hr_models.Shift.objects.filter(
            shifts_q,
            Q(date__shift_date=today, time__gte=now.timetz()) | Q(date__shift_date__gt=today),
            date__vacancy=vacancy,
            date__cancelled=False,
        ).annotate(
            accepted_vo_count=Sum(Case(
                When(vacancy_offers__status=hr_models.VacancyOffer.STATUS_CHOICES.accepted, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ))
        ).filter(accepted_vo_count__lt=F('workers')).select_related('date').order_by('date__shift_date', 'time'))

        if request.method == 'POST':
            return self.fillin_post(request, init_shifts)

        if not init_shifts:
            candidate_contacts = candidate_models.CandidateContact.objects.none()
        else:
            candidate_contacts = vacancy_utils.get_available_candidate_list(vacancy)

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
        partially_available = request.GET.get('available', 'True') == 'True'
        partially_available_candidates = {}
        if init_shifts:
            partially_available_candidates = vacancy_utils.get_partially_available_candidate_ids(
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

        candidate_contacts = candidate_contacts.annotate(
            distance_to_jobsite=Case(
                When(contact__distance_caches__jobsite=vacancy.jobsite,
                     then='contact__distance_caches__distance'),
                default=-1
            ),
            time_to_jobsite=Case(
                When(contact__distance_caches__jobsite=vacancy.jobsite,
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
            last_timesheet_date=Max('vacancy_offers__time_sheets__shift_started_at')
        ).prefetch_related('tag_rels__tag')

        restrict_radius = int(request.GET.get('distance_to_jobsite', -1))
        if restrict_radius > -1:
            candidate_contacts = candidate_contacts.filter(distance_to_jobsite__lte=restrict_radius * 1000)

        candidate_contacts = self.sort_candidates(request, candidate_contacts)

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
            candidate_contacts[:51], context=context, many=True
        )
        return Response({
            'shifts': [ApiBaseRelatedField.to_read_only_data(shift) for shift in init_shifts],
            'vacancy': vacacy_ctx,
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

                unavailable = vacancy_utils.get_partially_available_candidate_ids_for_vs(
                    candidate_models.CandidateContact.objects.filter(id=candidate_id),
                    shift.date.shift_date, shift.time
                )
                if len(unavailable) == 0:
                    hr_models.VacancyOffer.objects.create(
                        shift=shift,
                        candidate_contact_id=candidate_id,
                    )

        return Response({
            'status': 'ok',
        })

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

    def sort_candidates(self, request, candidate_contacts):
        params = request.query_params.get(api_settings.ORDERING_PARAM)
        if params:
            fields = [param.strip() for param in params.split(',')]

            return candidate_contacts.order_by(*fields)

        return candidate_contacts
