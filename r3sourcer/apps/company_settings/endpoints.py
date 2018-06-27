from django.utils.translation import ugettext_lazy as _
from drf_auto_endpoint.router import router

from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.company_settings.models import GlobalPermission


class GlobalPermissionEndpoint(ApiEndpoint):

    model = GlobalPermission

    serializer_fields = ('id', 'name', )

    list_display = ('name', )

    fieldsets = ('name', )
    list_editable = ('name', )

    list_editable_buttons = []

    filter_fields = ['user']
    search_fields = ['name']


router.register(endpoint=GlobalPermissionEndpoint())
