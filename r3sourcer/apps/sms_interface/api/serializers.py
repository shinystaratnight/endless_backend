from django.conf import settings

from r3sourcer.apps.core.api.fields import ApiBaseRelatedField
from r3sourcer.apps.core.api.serializers import ApiBaseModelSerializer
from r3sourcer.apps.core.models import Contact, Company
from r3sourcer.apps.core.utils.text import pluralize
from r3sourcer.apps.core_adapter.utils import api_reverse_lazy
from r3sourcer.apps.sms_interface import models as sms_models


class SMSMessageSerializer(ApiBaseModelSerializer):

    method_fields = ('delivered_received_datetime', 'related', 'from', 'to', 'can_resend')

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

        for related in obj.related_objects.all():
            if related.content_object is None:
                continue

            resp.append(self._related_item(related.content_object, related.content_type))

        return resp or '-'

    def _get_contact_by_number(self, phone_number):
        try:
            return Contact.objects.filter(phone_mobile=phone_number).latest('created_at')
        except Contact.DoesNotExist:
            return None

    def _get_company_by_number(self, phone_number):
        try:
            return Company.objects.filter(phone_numbers__phone_number=phone_number).latest('created_at')
        except Company.DoesNotExist:
            return None

    def get_from(self, obj):
        from_object = self._get_contact_by_number(obj.from_number)

        if from_object is None:
            from_object = self._get_company_by_number(obj.from_number)

        return from_object and ApiBaseRelatedField.to_read_only_data(from_object)

    def get_to(self, obj):
        to_object = self._get_contact_by_number(obj.to_number)

        if to_object is None:
            to_object = self._get_company_by_number(obj.to_number)

        return to_object and ApiBaseRelatedField.to_read_only_data(to_object)

    def get_can_resend(self, obj):
        return not obj.is_delivered()


class SMSLogSerializer(ApiBaseModelSerializer):

    method_fields = ('cost', )

    class Meta:
        model = sms_models.SMSMessage
        fields = ('sent_at', 'sid', 'type', 'from_number', 'to_number', 'segments', 'status')
        exclude_many = True

    def get_cost(self, obj):
        segment_cost = obj.company and hasattr(obj.company, 'sms_balance') and obj.company.sms_balance.segment_cost
        return segment_cost * obj.segments if segment_cost else 0
