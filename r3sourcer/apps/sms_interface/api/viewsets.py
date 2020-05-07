import logging

from django.db.models import Q
from rest_framework import viewsets, mixins, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from r3sourcer.apps.core.api.viewsets import BaseApiViewset
from r3sourcer.apps.sms_interface.models import SMSTemplate
from r3sourcer.apps.sms_interface.utils import get_sms_service


logger = logging.getLogger(__name__)


class SMSMessageViewset(BaseApiViewset):
    ordering = ('-created_at',)

    @action(methods=['post'], detail=True)
    def resend(self, request, pk, *args, **kwargs):
        sms_message = self.get_object()

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

        sms_interface.send(sms_message.to_number,
                           sms_message.text,
                           sms_message.from_number,
                           sms_message.related_object,
                           **data_dict)

        return Response({'status': 'success'})


class SMSMessageTemplateViewset(mixins.ListModelMixin,
                                mixins.CreateModelMixin,
                                mixins.UpdateModelMixin,
                                mixins.DestroyModelMixin,
                                viewsets.GenericViewSet):
    queryset = SMSTemplate.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(
            company_id=self.request.user.company.id
        )

    def perform_create(self, serializer):
        serializer.save(company_id=self.request.user.company.id)
