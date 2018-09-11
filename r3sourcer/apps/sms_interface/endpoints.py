from r3sourcer.apps.core.api.router import router

from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.sms_interface import models as sms_models
from r3sourcer.apps.sms_interface.api import serializers as sms_serializers, filters


class SMSMessageApiEndpoint(ApiEndpoint):

    model = sms_models.SMSMessage
    serializer = sms_serializers.SMSMessageSerializer
    filter_class = filters.SMSMessageFilter

    search_fields = ('from_number', 'to_number')


class SMSRelatedObjectEndpoint(ApiEndpoint):

    model = sms_models.SMSRelatedObject
    filter_class = filters.SMSRelatedObjectFilter


class SMSLogEndpoint(ApiEndpoint):

    model = sms_models.SMSMessage
    serializer = sms_serializers.SMSLogSerializer
    filter_class = filters.SMSMessageFilter

    search_fields = ('from_number', 'to_number', 'sid')


router.register(endpoint=SMSMessageApiEndpoint())
router.register(endpoint=SMSRelatedObjectEndpoint())
router.register(sms_models.SMSTemplate)
router.register(endpoint=SMSLogEndpoint(), url='sms-interface/smslogs')
