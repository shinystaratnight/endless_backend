import logging
from django.utils import timezone
from django.db import transaction
from drf_auto_endpoint.decorators import custom_action
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from django.utils.translation import ugettext_lazy as _

from r3sourcer.apps.candidate import models as candidate_models
from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.core.models import CompanyContact, Company
from r3sourcer.apps.core.utils.text import format_lazy
from r3sourcer.apps.core_adapter import constants
from r3sourcer.apps.core_adapter.utils import api_reverse_lazy
from r3sourcer.apps.hr import models as hr_models
from r3sourcer.apps.hr.api.serializers import timesheet as timesheet_serializers
from ..api import viewsets, filters

__all__ = [
    'TimeSheetEndpoint'
]

logger = logging.getLogger(__name__)


class TimeSheetEndpoint(ApiEndpoint):

    model = hr_models.TimeSheet
    base_viewset = viewsets.TimeSheetViewset
    serializer = timesheet_serializers.TimeSheetSerializer
    filter_class = filters.TimesheetFilter

    list_display = (
        {
            'label': _('Company / Jobsite / Supervisor'),
            'fields': ({
                'type': constants.FIELD_LINK,
                'field': 'company',
                'endpoint': format_lazy('{}{{company.id}}', api_reverse_lazy('core/companies')),
            }, {
                'type': constants.FIELD_LINK,
                'field': 'jobsite',
                'endpoint': format_lazy('{}{{jobsite.id}}', api_reverse_lazy('hr/jobsites')),
            }, {
                'type': constants.FIELD_LINK,
                'field': 'supervisor',
                'endpoint': format_lazy('{}{{supervisor.id}}', api_reverse_lazy('core/companycontacts')),
            }),
        }, {
            'label': _('Position / Candidate'),
            'fields': ({
                'type': constants.FIELD_LINK,
                'field': 'position',
                'endpoint': format_lazy('{}{{position.id}}', api_reverse_lazy('skills/skills')),
            }, {
                'type': constants.FIELD_LINK,
                'field': 'vacancy_offer.candidate_contact',
                'endpoint': format_lazy(
                    '{}{{vacancy_offer.candidate_contact.id}}',
                    api_reverse_lazy('candidate/candidatecontacts')
                ),
            }),
        }, {
            'label': _('Links'),
            'delim': ' / ',
            'fields': ({
                'type': constants.FIELD_LINK,
                'field': 'vacancy',
                'text': _('Vacancy'),
                'endpoint': format_lazy('{}{{vacancy.id}}', api_reverse_lazy('hr/vacancies')),
            }, ),
        }, {
            'label': _('Shift started/ended'),
            'fields': ('shift_started_ended',)
        }, {
            'label': _('Break started/ended'),
            'fields': ('break_started_ended',)
        }, {
            'label': _('Morning check'),
            'fields': ('going_to_work_confirmation', {
                'type': constants.FIELD_BUTTON,
                'icon': 'fa-commenting',
                'text': 'Candidate Going To Work',
                'endpoint': format_lazy(
                    '{}{{going_to_work_sent_sms.id}}',
                    api_reverse_lazy('sms-interface/smsmessages')
                ),
                'field': 'going_to_work_sent_sms',
                'action': constants.DEFAULT_ACTION_EDIT,
            }, {
                'type': constants.FIELD_BUTTON,
                'icon': 'fa-commenting',
                'text': 'Reply',
                'endpoint': format_lazy(
                    '{}{{going_to_work_reply_sms.id}}',
                    api_reverse_lazy('sms-interface/smsmessages')
                ),
                'field': 'going_to_work_reply_sms',
                'action': constants.DEFAULT_ACTION_EDIT,
            })
        },
    )

    def _get_all_supervisors(self):
        ids = hr_models.TimeSheet.objects.all().values_list(
            'supervisor', flat=True).distinct()
        return [
            {'label': str(jt), 'value': jt.id}
            for jt in CompanyContact.objects.filter(id__in=ids)
        ]

    def _get_all_candidates(self):
        ids = hr_models.TimeSheet.objects.all().values_list(
            'vacancy_offer__candidate_contact', flat=True).distinct()
        return [
            {'label': str(jt), 'value': jt.id}
            for jt in candidate_models.CandidateContact.objects.filter(id__in=ids)
        ]

    def _get_all_companies(self):
        ids = hr_models.TimeSheet.objects.all().values_list(
            'vacancy_offer__shift__date__vacancy__customer_company_id', flat=True
        ).distinct()
        return [
            {'label': str(jt), 'value': jt.id}
            for jt in Company.objects.filter(id__in=ids)
        ]

    def _get_all_jobsites(self):
        ids = hr_models.TimeSheet.objects.all().values_list(
            'vacancy_offer__shift__date__vacancy__jobsite_id', flat=True
        ).distinct()
        return [
            {'label': str(jt), 'value': jt.id}
            for jt in hr_models.Jobsite.objects.filter(id__in=ids)
        ]

    def get_list_filter(self):
        return [{
            'field': 'shift_started_at',
            'type': constants.FIELD_DATE,
        }, {
            'type': constants.FIELD_SELECT,
            'field': 'supervisor',
            'choices': self._get_all_supervisors,
            'is_qs': True,
        }, {
            'type': constants.FIELD_SELECT,
            'field': 'candidate',
            'label': _('Candidate Contact'),
            'choices': self._get_all_candidates,
            'is_qs': True,
        }, {
            'type': constants.FIELD_SELECT,
            'field': 'company',
            'label': _('Company'),
            'choices': self._get_all_companies,
            'is_qs': True,
        }, {
            'type': constants.FIELD_SELECT,
            'field': 'jobsite',
            'label': _('Jobsite'),
            'choices': self._get_all_jobsites,
            'is_qs': True,
        }]

    @transaction.atomic
    @custom_action(method='POST')
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

        logger.debug("TimeSheet {ts_id} approved through pin.".format(
            ts_id=time_sheet.id
        ))

        return Response(status=status.HTTP_200_OK)

    @transaction.atomic
    @custom_action(method='POST')
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
