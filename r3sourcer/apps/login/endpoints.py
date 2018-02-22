from drf_auto_endpoint.router import router

from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.core_adapter.constants import FIELD_PASSWORD

from .api import viewsets
from .models import TokenLogin


class LoginEndpoint(ApiEndpoint):

    model = TokenLogin
    viewset = viewsets.AuthViewSet

    fieldsets = (
        'username', {
            'type': FIELD_PASSWORD,
            'field': 'password'
        }
    )
    fields = ('username', 'password')


router.register(endpoint=LoginEndpoint(), url='auth')
router.register(TokenLogin)
