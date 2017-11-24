from drf_auto_endpoint.router import router

from django.utils.translation import ugettext_lazy as _
from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.core.api.viewsets import BaseApiViewset
from r3sourcer.apps.core_adapter import constants

from .. import models
from . import filters
from . import serializers


class ActivityViewset(BaseApiViewset):
    def get_queryset(self):
        if self.request.user.is_superuser:
            return models.Activity.objects.all()

        return models.Activity.objects.filter(
            contact__user_id=self.request.user.id
        )


class ActivityEndpoint(ApiEndpoint):
    model = models.Activity
    base_viewset = ActivityViewset
    filter_class = filters.ActivityFilter
    serializer = serializers.ActivitySerializer

    fieldsets = (
        'id', 'starts_at', 'ends_at', 'template',
        {'field': 'priority', 'type': constants.FIELD_SELECT},
        {'field': 'done', 'type': constants.FIELD_SELECT}
    )

    list_display = (
        'contact.__str__',
        'priority',
        {
            'label': _("Starts at"),
            'type': constants.FIELD_DATETIME,
            'field': 'starts_at'
        },
        {
            'label': _("Ends at"),
            'type': constants.FIELD_DATETIME,
            'field': 'ends_at'
        },
        'done'
    )

    list_filter = (
        'priority',
        'done',
        {
            'type': constants.FIELD_DATE,
            'field': 'starts_at'
        },
        {
            'type': constants.FIELD_DATE,
            'field': 'ends_at'
        }
    )

    list_editable = (
        'priority',
        {
            'label': _("Starts at"),
            'type': constants.FIELD_DATETIME,
            'field': 'starts_at'
        },
        {
            'label': _("Ends at"),
            'type': constants.FIELD_DATETIME,
            'field': 'ends_at'
        },
        'done'
    )


router.register(endpoint=ActivityEndpoint())
