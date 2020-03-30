from rest_framework import viewsets, mixins, permissions

from r3sourcer.apps.core.api.languages.serializers import LanguageSerializer
from r3sourcer.apps.core.models import Language


class LanguageViewSet(mixins.ListModelMixin,
                      viewsets.GenericViewSet):
    queryset = Language.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LanguageSerializer
    pagination_class = None
