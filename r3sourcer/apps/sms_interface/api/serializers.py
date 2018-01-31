from r3sourcer.apps.core.api.serializers import ApiBaseModelSerializer
from r3sourcer.apps.sms_interface import models as sms_models


class SMSMessageSerializer(ApiBaseModelSerializer):

    class Meta:
        model = sms_models.SMSMessage
        fields = '__all__'
        exclude_many = True
