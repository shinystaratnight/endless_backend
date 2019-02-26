import copy
import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import exception_handler, APIView

from r3sourcer.apps.company_settings.models import GlobalPermission
from r3sourcer.apps.core.api import serializers
from r3sourcer.apps.core import models
from r3sourcer.apps.core.tasks import send_trial_email, cancel_trial


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

    permission_classes = [permissions.AllowAny]

    @method_decorator(csrf_exempt)
    def post(self, request, **kwargs):
        data = copy.copy(request.data)
        data['website'] = '{}.{}'.format(data['website'], settings.REDIRECT_DOMAIN)

        serializer = serializers.TrialSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        phone_mobile = serializer.validated_data['phone_mobile']

        new_user = User.objects.create_user(email=email, phone_mobile=phone_mobile)
        contact = new_user.contact
        contact.first_name = serializer.validated_data['first_name']
        contact.last_name = serializer.validated_data['last_name']
        contact.save(update_fields=['first_name', 'last_name'])

        trial_role, created = models.Role.objects.get_or_create(name=models.Role.ROLE_NAMES.trial)
        new_user.role.add(trial_role)

        # set role and permissions
        permission_list = GlobalPermission.objects.all()
        new_user.user_permissions.add(*permission_list)
        new_user.trial_period_start = timezone.now()
        new_user.save()

        company = models.Company.objects.create(
            name=serializer.validated_data['company_name'],
            type=models.Company.COMPANY_TYPES.master,
        )

        models.CompanyRel.objects.create(master_company=company, regular_company=company)

        company_contact = models.CompanyContact.objects.create(contact=contact)
        models.CompanyContactRelationship.objects.create(company=company, company_contact=company_contact)

        domain = serializer.validated_data['website'].lower()
        site, created = Site.objects.get_or_create(domain=domain, defaults={'name': domain})
        models.SiteCompany.objects.get_or_create(company=company, site=site)

        models.Form.objects.get_or_create(
            company=company,
            builder=models.FormBuilder.objects.get(
                content_type=ContentType.objects.get_by_natural_key('candidate', 'candidatecontact')
            ),
            defaults=dict(
                title='Application Form',
                is_active=True,
                short_description='New application form',
                submit_message="You've been registered!"
            )
        )
        end_of_trial = timezone.now() + datetime.timedelta(days=30)

        send_trial_email.apply_async([contact.id, company.id], countdown=10)
        cancel_trial.apply_async([new_user.id], eta=end_of_trial)

        return Response({
            'status': 'success',
            'message': _('Trial User registered successfully')
        })
