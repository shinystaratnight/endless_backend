import logging
from django.utils import timezone
from django.db import transaction
from drf_auto_endpoint.decorators import custom_action
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from django.utils.translation import ugettext_lazy as _

from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.core.models import CompanyContact
from r3sourcer.apps.core_adapter import constants
from ..api.serializers.timesheet import (
    TimeSheetSignatureSerializer, PinCodeSerializer
)
from ..models import TimeSheet
from ..api import viewsets, filters

__all__ = [
    'TimeSheetEndpoint'
]

logger = logging.getLogger(__name__)


class TimeSheetEndpoint(ApiEndpoint):

    model = TimeSheet
    base_viewset = viewsets.TimeSheetViewset
    filter_class = filters.TimesheetFilter

    def _get_all_supervisors(self):
        ids = TimeSheet.objects.all().values_list(
            'supervisor', flat=True).distinct()
        return [
            {'label': str(jt), 'value': jt.id}
            for jt in CompanyContact.objects.filter(id__in=ids)
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
            'field': 'approved',

            'label': _('Status'),
            'choices': [{'label': 'Approved', 'value': 'True'},
                        {'label': 'Unapproved', 'value': 'False'}]
        }]

    @transaction.atomic
    @custom_action(method='POST')
    def approve_by_pin(self, request, pk, *args, **kwargs):
        """
        Approval action to timesheet.
        Would be used for approving through pin code.
        """

        time_sheet = get_object_or_404(TimeSheet.objects.select_for_update(), pk=pk)

        serializer = PinCodeSerializer(instance=time_sheet, data=request.data)
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

        time_sheet = get_object_or_404(TimeSheet.objects.select_for_update(), pk=pk)

        # check if already approved
        if time_sheet.supervisor_approved_at:
            return Response({
                "description": _("TimeSheet already confirmed")
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = TimeSheetSignatureSerializer(instance=time_sheet, data=request.data)
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
