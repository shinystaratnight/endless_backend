import copy

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status, authentication
from rest_framework.response import Response
from rest_framework.views import exception_handler, APIView

from r3sourcer.apps.core.api import serializers
from r3sourcer.apps.core import models
from r3sourcer.apps.core.tasks import send_trial_email


User = get_user_model()


def core_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        new_response = {
            'status': 'error',
            'errors': response.data
        }
        response.data = new_response
    elif exc and hasattr(exc, 'messages'):
        data = {
            'status': 'error',
            'errors': {"non_field_errors": exc.messages if hasattr(exc, 'messages') else str(exc)}
        }
        response = Response(data, status=status.HTTP_400_BAD_REQUEST)

    return response


class TrialUserView(APIView):
    authentication_classes = (authentication.TokenAuthentication, )

    @method_decorator(csrf_exempt)
    def post(self, request, **kwargs):
        data = copy.copy(request.data)
        data['website'] = '%s.r3sourcer.com' % data['website']

        serializer = serializers.TrialSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        phone_mobile = serializer.validated_data['phone_mobile']

        new_password = User.objects.make_random_password()
        new_user = User.objects.create_user(password=new_password, email=email, phone_mobile=phone_mobile)
        contact = new_user.contact
        contact.first_name = serializer.validated_data['first_name']
        contact.last_name = serializer.validated_data['last_name']
        contact.save(update_fields=['first_name', 'last_name'])

        company = models.Company.objects.create(
            name=serializer.validated_data['company_name'],
            type=models.Company.COMPANY_TYPES.master,
        )

        company_contact = models.CompanyContact.objects.create(contact=contact)
        models.CompanyContactRelationship.objects.create(company=company, company_contact=company_contact)

        send_trial_email.apply_async([contact.id, new_password], countdown=10)

        domain = serializer.validated_data['website']
        site, created = Site.objects.get_or_create(domain=domain, defaults={'name': domain})
        models.SiteCompany.objects.get_or_create(company=company, site=site)

        return Response({
            'status': 'success',
            'message': _('Trial User registered successfully')
        })
