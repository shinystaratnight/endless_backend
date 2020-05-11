from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.core.api.router import router
from r3sourcer.apps.email_interface.api import viewsets
from r3sourcer.apps.email_interface.api.serializers import EmailTemplateSerializer
from r3sourcer.apps.email_interface.models import EmailTemplate


class EmailTemplateEndpoint(ApiEndpoint):

    model = EmailTemplate
    base_viewset = viewsets.EmailMessageTemplateViewset
    serializer = EmailTemplateSerializer


router.register(endpoint=EmailTemplateEndpoint())
