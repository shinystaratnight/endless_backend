import logging

from rest_framework import viewsets, mixins, permissions

from r3sourcer.apps.core.api.viewsets import BaseApiViewset
from r3sourcer.apps.email_interface.models import EmailTemplate

logger = logging.getLogger(__name__)


class EmailMessageViewset(BaseApiViewset):
    ordering = ('-created_at',)

    def get_queryset(self):
        return self.queryset.filter(template__company_id=self.request.user.company.id)


class EmailMessageTemplateViewset(mixins.ListModelMixin,
                                  mixins.CreateModelMixin,
                                  mixins.UpdateModelMixin,
                                  mixins.DestroyModelMixin,
                                  mixins.RetrieveModelMixin,
                                  viewsets.GenericViewSet):
    queryset = EmailTemplate.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(
            company_id=self.request.user.company.id
        )

    def perform_create(self, serializer):
        serializer.save(company_id=self.request.user.company.id)