from r3sourcer.apps.core.api.router import router

from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.sms_interface import models as sms_models
from r3sourcer.apps.sms_interface.api import serializers as sms_serializers, filters


class SMSMessageApiEndpoint(ApiEndpoint):

    model = sms_models.SMSMessage
    serializer = sms_serializers.SMSMessageSerializer
    filter_class = filters.SMSMessageFilter


class SMSRelatedObjectEndpoint(ApiEndpoint):

    model = sms_models.SMSRelatedObject
    filter_class = filters.SMSRelatedObjectFilter


router.register(endpoint=SMSMessageApiEndpoint())
router.register(endpoint=SMSRelatedObjectEndpoint())
router.register(sms_models.SMSTemplate)
