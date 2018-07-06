from r3sourcer.apps.core.api.router import router

from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.activity.api import viewsets, filters, serializers

from . import models


class ActivityEndpoint(ApiEndpoint):
    model = models.Activity
    base_viewset = viewsets.ActivityViewset
    filter_class = filters.ActivityFilter
    serializer = serializers.ActivitySerializer


router.register(endpoint=ActivityEndpoint())
