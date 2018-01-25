from drf_auto_endpoint.router import router

from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.sms_interface import models as sms_models
from r3sourcer.apps.sms_interface.api import serializers as sms_serializers


class SMSMessageApiEndpoint(ApiEndpoint):
    model = sms_models.SMSMessage
    serializer = sms_serializers.SMSMessageSerializer


router.register(endpoint=SMSMessageApiEndpoint())
router.register(sms_models.SMSRelatedObject)
