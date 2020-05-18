from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.core.api.router import router
from r3sourcer.apps.email_interface.api import viewsets
from r3sourcer.apps.email_interface.api.filters import EmailMessageFilter
from r3sourcer.apps.email_interface.api.serializers import EmailTemplateSerializer, EmailMessageSerializer
from r3sourcer.apps.email_interface.models import EmailTemplate, EmailMessage


class EmailTemplateEndpoint(ApiEndpoint):

    model = EmailTemplate
    base_viewset = viewsets.EmailMessageTemplateViewset
    serializer = EmailTemplateSerializer


class EmailMessageApiEndpoint(ApiEndpoint):

    model = EmailMessage
    serializer = EmailMessageSerializer
    base_viewset = viewsets.EmailMessageViewset
    filter_class = EmailMessageFilter

    search_fields = ('from_number', 'to_number')


router.register(endpoint=EmailMessageApiEndpoint())
router.register(endpoint=EmailTemplateEndpoint())
