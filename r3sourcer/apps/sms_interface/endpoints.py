from drf_auto_endpoint.router import router

from r3sourcer.apps.core.api.serializers import ApiBaseModelSerializer
from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.sms_interface import models as sms_models


class SMSMessageSerializer(ApiBaseModelSerializer):

    class Meta:
        model = sms_models.SMSMessage
        fields = '__all__'
        exclude_many = True


class SMSMessageApiEndpoint(ApiEndpoint):
    model = sms_models.SMSMessage
    serializer = SMSMessageSerializer


router.register(endpoint=SMSMessageApiEndpoint())
router.register(sms_models.SMSRelatedObject)
