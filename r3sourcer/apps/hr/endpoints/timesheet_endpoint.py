import logging
from django.utils import timezone
from django.db import transaction
from drf_auto_endpoint.decorators import custom_action
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from django.utils.translation import ugettext_lazy as _

from r3sourcer.apps.core.api.endpoints import ApiEndpoint
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
            'label': _('Client / Jobsite / Supervisor'),
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
            'label': _('Confirmations'),
            'fields': ({
                'type': constants.FIELD_STATIC_ICON,
                'label': _('Morning check'),
                'field': 'going_to_work_confirmation',
                'showIf': [
                    {
                        'going_to_work_confirmation': True,
                    }
                ],
            }, {
                'type': constants.FIELD_BUTTON,
                'icon': 'fa-external-link',
                'label': '%s:' % _('Morning check'),
                'text': _('Confirm'),
                'endpoint': format_lazy(
                    '{}{{company.id}}/confirm',
                    api_reverse_lazy('hr/timesheets'),
                ),
                'field': 'going_to_work_confirmation',
                'action': constants.DEFAULT_ACTION_POST,
                'showIf': [
                    {
                        'going_to_work_confirmation': False,
                    }
                ],
            }, {
                'type': constants.FIELD_STATIC_ICON,
                'label': _('Candidate filled'),
                'field': 'candidate_filled',
                'showIf': [
                    {
                        'candidate_filled': True,
                    }
                ],
            }, {
                'type': constants.FIELD_BUTTON,
                'icon': 'fa-external-link',
                'text': _('Send TS SMS'),
                'endpoint': format_lazy(
                    '{}{{company.id}}/resend_sms',
                    api_reverse_lazy('hr/timesheets'),
                ),
                'field': 'resend_sms_candidate',
                'action': constants.DEFAULT_ACTION_POST,
                'showIf': [
                    {
                        'resend_sms_candidate': True,
                    }
                ],
            }, {
                'type': constants.FIELD_STATIC,
                'label': _('Supervisor approved'),
                'field': 'supervisor_approved',
            }, {
                'type': constants.FIELD_BUTTON,
                'icon': 'fa-external-link',
                'text': _('Send TS SMS'),
                'endpoint': format_lazy(
                    '{}{{company.id}}/resend_sms',
                    api_reverse_lazy('hr/timesheets'),
                ),
                'field': 'resend_sms_supervisor',
                'action': constants.DEFAULT_ACTION_POST,
                'showIf': [
                    {
                        'resend_sms_supervisor': True,
                    }
                ],
            }, {
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
        }, {
            'label': _('Confirmations'),
            'fields': ({
                'type': constants.FIELD_BUTTON,
                'icon': 'fa-external-link',
                'text': _('Fill'),
                'endpoint': format_lazy(
                    '{}{{id}}/candidate_fill',
                    api_reverse_lazy('hr/timesheets'),
                ),
                'field': 'id',
                'action': constants.DEFAULT_ACTION_EDIT,
                'showIf': [
                    {
                        'resend_sms_candidate': True,
                    }
                ],
            }, {
                'type': constants.FIELD_BUTTON,
                'icon': 'fa-external-link',
                'text': _('Approve'),
                'endpoint': format_lazy(
                    '{}{{id}}/supervisor_approve',
                    api_reverse_lazy('hr/timesheets'),
                ),
                'field': 'id',
                'action': constants.DEFAULT_ACTION_EDIT,
                'showIf': [
                    {
                        'resend_sms_supervisor': True,
                    }
                ],
            },),
        },
    )

    fieldsets = (
        'id', 'vacancy_offer', 'going_to_work_sent_sms', 'going_to_work_reply_sms', 'going_to_work_confirmation',
        'shift_started_at', 'break_started_at', 'break_ended_at', 'shift_ended_at', 'supervisor',
        'candidate_submitted_at', 'supervisor_approved_at', 'candidate_rate', 'rate_overrides_approved_by',
        'rate_overrides_approved_at', 'created_at', 'updated_at', {
            'field': 'related_sms',
            'type': constants.FIELD_RELATED,
            'many': True,
            'endpoint': api_reverse_lazy('sms-interface/smsmessages'),
        }
    )

    def get_list_filter(self):
        return [{
            'field': 'shift_started_at',
            'type': constants.FIELD_DATE,
        }, {
            'type': constants.FIELD_RELATED,
            'field': 'supervisor',
            'related_endpoint': 'core/companycontacts',
        }, {
            'type': constants.FIELD_RELATED,
            'field': 'candidate',
            'label': _('Candidate Contact'),
            'related_endpoint': 'candidate/candidatecontacts',
        }, {
            'type': constants.FIELD_RELATED,
            'field': 'company',
            'label': _('Client'),
            'endpoint': api_reverse_lazy('core/companies'),
        }, {
            'type': constants.FIELD_RELATED,
            'field': 'jobsite',
            'label': _('Jobsite'),
            'endpoint': api_reverse_lazy('hr/jobsites'),
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
