from django.contrib.contenttypes.models import ContentType

from rest_framework import generics
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SMSTemplate
from .mixins import MessageViewBase
from .serializers import TemplateBodySerializer, ContentTypeSerializer, TemplateSerializer


class TemplateCompileView(MessageViewBase, APIView):

    permissions = (permissions.IsAdminUser, )

    recipient_field = 'phone_mobile'
    sender_value_field = 'get_phone'
    message_type = 'sms'

    def post(self, request, *args, **kwargs):
        serializer = TemplateBodySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        compiled_messages = []
        for recipient in self.get_recipients():
            params = self.get_url_params()
            params.update(**self.get_extra_params(recipient))
            params.update(**self.get_json_params(serializer.validated_data['params']))
            compiled_messages.append(
                SMSTemplate.compile_string(serializer.validated_data['body'], **params)[0]
            )
        return Response({'body': compiled_messages})


class ContentTypeListView(generics.ListAPIView):

    permissions = (permissions.IsAdminUser, )
    pagination_class = None
    queryset = ContentType.objects.filter(app_label__in=[
        'core',
        'crm_core',
        'crm_hr'
    ])
    serializer_class = ContentTypeSerializer


class TemplateSMSMessageListView(generics.ListAPIView):

    permission_classes = (permissions.IsAdminUser, )
    pagination_class = None
    queryset = SMSTemplate.objects.filter(type=SMSTemplate.SMS)
    serializer_class = TemplateSerializer
