from r3sourcer.apps.core.api.serializers import ApiBaseModelSerializer
from r3sourcer.apps.core.utils.text import pluralize
from r3sourcer.apps.core_adapter.utils import api_reverse_lazy
from r3sourcer.apps.sms_interface import models as sms_models


class SMSMessageSerializer(ApiBaseModelSerializer):

    method_fields = ('delivered_received_datetime', 'related')

    class Meta:
        model = sms_models.SMSMessage
        fields = '__all__'
        exclude_many = True
        extra_kwargs = {
            'to_number': {'required': True}
        }

    def get_delivered_received_datetime(self, obj):
        if obj.type == sms_models.SMSMessage.TYPE_CHOICES.SENT:
            if obj.status == sms_models.SMSMessage.STATUS_CHOICES.DELIVERED:
                return obj.updated_at
        if obj.type == sms_models.SMSMessage.TYPE_CHOICES.RECEIVED:
            return obj.updated_at

    def _related_item(self, related, related_ct):
        return {
            '__str__': '%s: %s' % (related_ct.name, str(related)),
            'endpoint':
                api_reverse_lazy('{}/{}'.format(
                    related_ct.app_label.replace('_', '-'), pluralize(related_ct.model)
                ), methodname='detail', pk=related.id),
        }

    def get_related(self, obj):
        if obj.related_object:
            resp = [self._related_item(obj.related_object, obj.related_content_type)]
        else:
            resp = []

        for related in obj.get_related_objects():
            resp.append(self._related_item(related.content_object, related.content_type))

        return resp or '-'
