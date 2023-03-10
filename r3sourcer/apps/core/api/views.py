import copy
import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import exception_handler

from r3sourcer.apps.company_settings.models import GlobalPermission
from r3sourcer.apps.core import models
from r3sourcer.apps.core.api import serializers
from r3sourcer.apps.core.tasks import send_trial_email, cancel_trial, send_contact_verify_sms
from r3sourcer.helpers.datetimes import utc_now, tz2utc

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


class TrialUserView(viewsets.GenericViewSet):

    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.TrialSerializer

    @method_decorator(csrf_exempt)
    def create(self, request, *args, **kwargs):
        data = copy.copy(request.data)

        serializer = serializers.TrialSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        phone_mobile = serializer.validated_data['phone_mobile']

        new_user = User.objects.create_user(email=email, phone_mobile=phone_mobile)
        contact = new_user.contact
        contact.first_name = serializer.validated_data['first_name']
        contact.last_name = serializer.validated_data['last_name']
        contact.save(update_fields=['first_name', 'last_name'])

        trial_role = models.Role.objects.create(name=models.Role.ROLE_NAMES.manager)
        new_user.role.add(trial_role)

        # set role and permissions
        permission_list = GlobalPermission.objects.all()
        new_user.user_permissions.add(*permission_list)
        new_user.trial_period_start = utc_now()
        new_user.save()

        company_contact = models.CompanyContact.objects.create(contact=contact)

        company = models.Company.objects.create(
            name=serializer.validated_data['company_name'],
            type=models.Company.COMPANY_TYPES.master,
            primary_contact=company_contact,
        )

        models.CompanyRel.objects.create(master_company=company, regular_company=company)

        models.CompanyContactRelationship.objects.create(company=company, company_contact=company_contact)

        domain = '{}.{}'.format(serializer.validated_data['website'].lower(), settings.REDIRECT_DOMAIN)
        site, created = Site.objects.get_or_create(domain=domain, defaults={'name': domain})
        models.SiteCompany.objects.get_or_create(company=company, site=site)

        form, form_created = models.Form.objects.get_or_create(
            company=company,
            builder=models.FormBuilder.objects.get(
                content_type=ContentType.objects.get_by_natural_key('candidate', 'candidatecontact')
            ),
            defaults=dict(
                is_active=True
            )
        )

        models.FormLanguage.objects.get_or_create(
            form=form,
            title='Application Form',
            short_description='New application form',
            result_messages="You've been registered!"
        )

        end_of_trial = utc_now() + datetime.timedelta(days=30)

        send_trial_email.apply_async([contact.id, company.id], countdown=10)
        utc_end_of_trial = tz2utc(end_of_trial)
        cancel_trial.apply_async([new_user.id], eta=utc_end_of_trial)

        send_contact_verify_sms.apply_async(args=(contact.id, contact.id))

        return Response({
            'status': 'success',
            'message': _('Trial User registered successfully')
        })
