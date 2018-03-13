from django.utils.translation import ugettext_lazy as _
from drf_auto_endpoint.router import router

from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.core.utils.text import format_lazy
from r3sourcer.apps.core_adapter.utils import api_reverse_lazy
from r3sourcer.apps.core_adapter import constants
from r3sourcer.apps.sms_interface import models as sms_models
from r3sourcer.apps.sms_interface.api import serializers as sms_serializers


class SMSMessageApiEndpoint(ApiEndpoint):
    model = sms_models.SMSMessage
    serializer = sms_serializers.SMSMessageSerializer

    list_display = (
        'sid', {
            'type': constants.FIELD_LINK,
            'field': 'template',
            'endpoint': format_lazy('{}{{template.id}}', api_reverse_lazy('sms-interface/smstemplates'))
        },
        'from_number', 'to_number', 'status', 'sent_at', 'delivered_received_datetime',
        {
            'type': constants.FIELD_STATIC,
            'field': 'related',
            'label': _('Links')
        }
    )

    fieldsets = (
        'from_number', 'to_number', 'text', 'type', 'status', 'template', 'sent_at', 'created_at', 'reply_timeout',
        'delivery_timeout', 'error_message',
        {
            'field': 'related',
            'type': constants.FIELD_RELATED,
            'many': True,
        },
    )

    list_filter = ('type', 'status', 'template', {
        'field': 'created_at',
        'type': constants.FIELD_DATE,
    }, 'check_reply', 'is_fake')


router.register(endpoint=SMSMessageApiEndpoint())
router.register(sms_models.SMSRelatedObject, filter_fields=['sms'])
router.register(sms_models.SMSTemplate)
