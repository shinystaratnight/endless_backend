import logging

from rest_framework.decorators import action
from rest_framework.response import Response

from r3sourcer.apps.core.api.viewsets import BaseApiViewset
from r3sourcer.apps.sms_interface.models import SMSTemplate
from r3sourcer.apps.sms_interface.utils import get_sms_service


logger = logging.getLogger(__name__)


class SMSMessageViewset(BaseApiViewset):

    @action(methods=['post'], detail=True)
    def resend(self, request, pk, *args, **kwargs):
        sms_message = self.get_object()

        if not sms_message.is_delivered():
            sms_id = sms_message.id
            logger.info("Resending failed sms: {sms_id}".format(sms_id=sms_id))

            try:
                sms_interface = get_sms_service()
            except ImportError:
                logger.exception('Cannot load SMS service')
                return

            data_dict = {
                'related_objs': list(sms_message.related_objects.values('object_id', 'content_type')),
                'delivery_timeout': sms_message.delivery_timeout,
                'reply_timeout': sms_message.reply_timeout,
                'template': sms_message.template,
            }

            sms_interface.send(
                sms_message.to_number, sms_message.text, sms_message.from_number, sms_message.related_object,
                **data_dict
            )

        return Response({'status': 'success'})


class SMSMessageTemplateViewset(BaseApiViewset):

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        return queryset.filter(company=None)

    def get_object(self):
        obj = super().get_object()
        try:
            obj = self.queryset.get(name=obj.name, company=self.request.user.company)
            return obj
        except obj.DoesNotExist:
            obj = super().get_object()
            return obj

    def perform_update(self, serializer):
        if not serializer.validated_data.get('company'):
            self.request.data['company'] = self.request.user.company
            self.request.data.pop('id')
            SMSTemplate.objects.create(**self.request.data)
        else:
            serializer.save()
