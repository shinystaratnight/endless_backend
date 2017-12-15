import datetime

from django.db import transaction
from django.db.models import Q, Case, When, BooleanField
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import ugettext_lazy as _
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from filer.models import File

from r3sourcer.apps.core.api.viewsets import BaseApiViewset
from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.core.api.decorators import detail_route, list_route
from r3sourcer.apps.core.models.constants import CANDIDATE
from r3sourcer.apps.core.utils.text import format_lazy
from r3sourcer.apps.core_adapter import constants
from r3sourcer.apps.core_adapter.utils import api_reverse_lazy

from .serializers.timesheet import (
    TimeSheetSerializer, CandidateEvaluationSerializer
)
from r3sourcer.apps.hr import models as hr_models
from ..payment import InvoiceService


class ExtranetTimesheetEndpoint(ApiEndpoint):

    model = hr_models.TimeSheet
    serializer = TimeSheetSerializer

    list_buttons = []


class TimeSheetViewset(BaseApiViewset):

    TIME_FORM = {
        'type': constants.CONTAINER_ROW,
        'fields': ('shift_started_at', 'break_started_at',
                   'break_ended_at', 'shift_ended_at')
    }

    EVAL_FIELDS = ('was_on_time', 'was_motivated', 'had_ppe_and_tickets',
                   'met_expectations', 'representation')

    def get_queryset(self):

        contact = self.request.user.contact
        role = contact.get_role()

        queryset = hr_models.TimeSheet.objects.annotate(
            approved=Case(When(candidate_submitted_at__isnull=False, supervisor_approved_at__isnull=False, then=True),
                          output_field=BooleanField(), default=False)
        ).order_by('approved')

        if role == CANDIDATE:
            queryset = queryset.filter(
                vacancy_offer__candidate_contact_id=contact.candidate_contacts.id
            )
        return queryset


    def submit_hours(self, data, time_sheet, is_candidate=True):
        if is_candidate:
            data.update(candidate_submitted_at=timezone.now())
        else:
            data.update(supervisor_approved_at=timezone.now())
        serializer = TimeSheetSerializer(
            time_sheet, data=data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(serializer.data)

    def get_unapproved_queryset(self, request):
        now = timezone.now()
        ended_at = now - datetime.timedelta(hours=4)
        signed_delta = now - datetime.timedelta(hours=1)
        queryset = hr_models.TimeSheet.objects.filter(
            Q(candidate_submitted_at__isnull=False) |
            Q(shift_ended_at__lt=ended_at),
            Q(supervisor_approved_at__isnull=True) |
            Q(supervisor_approved_at__gte=signed_delta),
            supervisor__contact=request.user.contact,
            going_to_work_confirmation=True,
        ).distinct()
        return queryset

    def handle_request(self, request, pk, is_candidate=True, *args, **kwargs):
        time_sheet = get_object_or_404(
            hr_models.TimeSheet.objects.select_for_update(), pk=pk
        )

        if request.method == 'PUT':
            return self.submit_hours(
                kwargs.get('data', request.data), time_sheet, is_candidate
            )

        serializer = TimeSheetSerializer(time_sheet)
        return Response(serializer.data)

    def paginated(self, queryset):  # pragma: no cover
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = TimeSheetSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = TimeSheetSerializer(queryset, many=True)
        return Response(serializer.data)

    def handle_history(self, request):
        qry = Q(going_to_work_confirmation=True)
        if request.user.is_authenticated:
            contact = request.user.contact
            if contact.company_contact.exists():
                qry &= Q(supervisor_approved_at__isnull=False)
            else:
                qry &= Q(candidate_submitted_at__isnull=False)

        queryset = hr_models.TimeSheet.objects.filter(qry)

        return self.paginated(queryset)

    @transaction.atomic
    @detail_route(
        methods=['GET', 'PUT'],
        serializer=TimeSheetSerializer,
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

    @transaction.atomic
    @detail_route(methods=['PUT'])
    def approve(self, request, pk, *args, **kwargs):  # pragma: no cover
        return self.handle_request(request, pk, False, data={},
                                   *args, **kwargs)

    @transaction.atomic
    @detail_route(
        methods=['PUT'],
        serializer=TimeSheetSerializer,
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
        serializer=CandidateEvaluationSerializer,
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
        eval_serializer = CandidateEvaluationSerializer(data=request.data)
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
            pdf_file_obj = InvoiceService.generate_pdf(invoice)

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
