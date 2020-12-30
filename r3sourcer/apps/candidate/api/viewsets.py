from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Q, Exists
from django.utils.translation import ugettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from rest_framework import status, exceptions, permissions as drf_permissions, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from r3sourcer.apps.acceptance_tests.api.serializers import AcceptanceTestCandidateWorkflowSerializer
from r3sourcer.apps.acceptance_tests.models import AcceptanceTestWorkflowNode
from r3sourcer.apps.candidate.api.filters import CandidateContactAnonymousFilter
from r3sourcer.apps.core import tasks as core_tasks
from r3sourcer.apps.core.api.permissions import SiteContactPermissions
from r3sourcer.apps.core.api.viewsets import BaseApiViewset, BaseViewsetMixin
from r3sourcer.apps.core.models import Company, InvoiceRule, Workflow, WorkflowObject
from r3sourcer.apps.core.utils.companies import get_site_master_company
from r3sourcer.apps.hr.models import Job, TimeSheet
from r3sourcer.apps.logger.main import location_logger
from r3sourcer.apps.myob.models import MYOBSyncObject
from r3sourcer.helpers.datetimes import utc_now
from . import serializers
from ..models import Subcontractor, CandidateContact, CandidateContactAnonymous, CandidateRel, VisaType, \
                     CountryVisaTypeRelation, Formality
from ..tasks import buy_candidate
from ...core.utils.utils import normalize_phone_number


class CandidateContactViewset(BaseApiViewset):
    def perform_create(self, serializer):
        instance = serializer.save()

        manager = self.request.user.contact
        master_company = get_site_master_company(request=self.request)

        if not instance.contact.phone_mobile_verified:
            core_tasks.send_contact_verify_sms.apply_async(args=(instance.contact.id, manager.id))
        if not instance.contact.email_verified:
            core_tasks.send_contact_verify_email.apply_async(
                args=(instance.contact.id, manager.id, master_company.id))

    def perform_destroy(self, instance):
        has_joboffers = instance.job_offers.exists()

        if has_joboffers:
            raise exceptions.ValidationError({'non_field_errors': _('Cannot delete')})
        # delete all releted models to client contact
        instance.bank_account = None
        instance.save()
        instance.contact.bank_accounts.all().delete()
        instance.contact.user.delete()

    def validate_contact(self, contact, data):
        master_company = get_site_master_company(request=self.request)
        if not master_company:
            raise ValidationError(_('Master company not found'))

        country_code = master_company.get_hq_address().address.country.code2

        for field in contact._meta.fields:
            if not isinstance(field, PhoneNumberField):
                continue

            value = data.get(field.name)
            if not value:
                continue

            data[field.name] = normalize_phone_number(value, country_code)
        return data

    def update(self, request, *args, **kwargs):
        data = self.prepare_related_data(request.data)
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        myob_name = data.pop('myob_name', None)
        if myob_name:
            master_company = get_site_master_company(request=self.request)
            MYOBSyncObject.objects.update_or_create(
                record=instance.pk, app='candidate', model='CandidateContact',
                company=master_company, defaults={
                    'legacy_confirmed': True,
                    'legacy_myob_card_number': myob_name
                }
            )
        data['contact'] = self.validate_contact(instance.contact, data.get('contact', {}))
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(self.get_serializer(self.get_object()).data)

    @action(methods=['post'], detail=False, permission_classes=[drf_permissions.AllowAny])
    def register(self, request, *args, **kwargs):
        serializer = serializers.CandidateContactRegisterSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        serializer = serializers.CandidateContactSerializer(instance)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data,
                        status=status.HTTP_201_CREATED,
                        headers=headers)

    @action(methods=['get'], detail=True)
    def profile(self, request, pk, *args, **kwargs):
        return self.retrieve(request, pk=pk, *args, **kwargs)

    @action(methods=['post'], detail=False)
    def sendsms(self, request, *args, **kwargs):
        id_list = request.data

        if not id_list or not isinstance(id_list, list):
            raise exceptions.ParseError(_('You should select Company addresses'))

        phone_numbers = CandidateContact.objects.filter(
            id__in=id_list, contact__phone_mobile__isnull=False
        ).values_list(
            'contact__phone_mobile', flat=True
        ).distinct()

        return Response({
            'status': 'success',
            'phone_number': phone_numbers,
            'message': _('Phones numbers was selected'),
        })

    @action(methods=['get'], detail=False)
    def pool(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            queryset = CandidateContactAnonymous.objects.none()
        else:
            company = request.user.contact.get_closest_company()
            master_company = company.get_closest_master_company()
            queryset = CandidateContactAnonymous.objects.exclude(
                Q(candidate_rels__master_company=master_company) | Q(profile_price__lte=0)
                | Q(candidate_rels__owner=False)
            ).distinct()
            queryset = queryset.annotate(a=Exists(WorkflowObject.objects.filter(object_id__in=[str(i.id) for i in queryset],
                                                                        state__name_after_activation='Recruited - Available for Hire'))).filter(a=True)
        filtered_data = CandidateContactAnonymousFilter(request.GET, queryset=queryset)
        filtered_qs = filtered_data.qs

        return self._paginate(request, serializers.CandidatePoolSerializer, filtered_qs)

    @action(methods=['get'], detail=True)
    def pool_detail(self, request, pk, *args, **kwargs):
        if not request.user.is_authenticated():
            instance = CandidateContactAnonymous.objects.none()
        else:
            instance = self.get_object()
        serializer = serializers.CandidatePoolDetailSerializer(instance)

        return Response(serializer.data)

    @action(methods=['post'], detail=True, permission_classes=[SiteContactPermissions])
    def buy(self, request, pk, *args, **kwargs):
        master_company = request.user.contact.get_closest_company().get_closest_master_company()
        manager = request.user.contact.company_contact.first()
        candidate_contact = self.get_object()
        company = request.data.get('company')

        is_owner = CandidateRel.objects.filter(
            candidate_contact=candidate_contact, owner=True
        ).exists()
        if not is_owner:
            raise exceptions.ValidationError({
                'company': _('{company} cannot sell this candidate.').format(company=master_company)
            })

        try:
            company = Company.objects.get(pk=company)
        except Company.DoesNotExist:
            raise exceptions.ValidationError({'company': _('Cannot find company')})

        if company.type != Company.COMPANY_TYPES.master:
            raise exceptions.ValidationError({'company': _("Only Master company can buy candidate's profile")})

        existing_rel = CandidateRel.objects.filter(
            master_company=company, candidate_contact=candidate_contact
        ).first()
        if existing_rel:
            raise exceptions.ValidationError({'company': _('Company already has this Candidate Contact')})

        if not company.stripe_customer:
            raise exceptions.ValidationError({'company': _('Company has no billing information')})

        if candidate_contact.profile_price:
            rel = CandidateRel.objects.create(
                master_company=company, candidate_contact=candidate_contact, owner=False, active=False,
                company_contact=manager
            )

            buy_candidate.apply_async([rel.id, str(request.user.id)])

        return Response({'status': 'success', 'message': _('Please wait for payment to complete')})

    @action(methods=['get'], detail=True)
    def tests(self, request, *args, **kwargs):
        candidate = self.get_object()

        qry = Q(
            acceptance_test__acceptance_tests_skills__isnull=True,
            acceptance_test__acceptance_tests_tags__isnull=True,
            acceptance_test__acceptance_tests_industries__isnull=True,
        )

        closest_company = candidate.get_closest_company()
        if closest_company.industries.all() is not None:
            qry |= Q(acceptance_test__acceptance_tests_industries__industry_id__in=closest_company.industries.all().values_list('id'))

        if hasattr(candidate, 'candidate_skills'):
            skill_ids = candidate.candidate_skills.values_list('skill', flat=True)
            qry |= Q(acceptance_test__acceptance_tests_skills__skill_id__in=skill_ids)

        if hasattr(candidate, 'tag_rels'):
            tag_ids = candidate.tag_rels.values_list('tag', flat=True)
            qry |= Q(acceptance_test__acceptance_tests_tags__tag_id__in=tag_ids)

        workflow = Workflow.objects.get(model=ContentType.objects.get_for_model(candidate))

        tests = AcceptanceTestWorkflowNode.objects.filter(
            qry, company_workflow_node__workflow_node__workflow=workflow,
            company_workflow_node__company=closest_company
        ).distinct()

        serializer = AcceptanceTestCandidateWorkflowSerializer(tests, many=True, object_id=candidate.id)

        return Response(serializer.data, status=status.HTTP_200_OK)


class SubcontractorViewset(BaseApiViewset):

    http_method_names = ['post', 'put', 'get', 'options']

    @action(methods=['post'], detail=False)
    def register(self, request, *args, **kwargs):
        serializer = serializers.CandidateContactRegisterSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        candidate = serializer.save()
        company = Company.objects.create(
            name=str(candidate),
            expense_account='6-1006'
        )

        instance = Subcontractor.objects.create(
            company=company,
            primary_contact=candidate
        )

        InvoiceRule.objects.create(company=company)

        serializer = serializers.SubcontractorSerializer(instance)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data,
                        status=status.HTTP_201_CREATED,
                        headers=headers)


class CandidateLocationViewset(BaseViewsetMixin,
                               mixins.UpdateModelMixin,
                               viewsets.GenericViewSet):

    queryset = CandidateContact.objects.all()
    serializer_class = serializers.CandidateContactSerializer
    permission_classes = [drf_permissions.IsAuthenticated]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        locations = request.data.get('locations', [])
        for location in locations:
            latitude = location.get('latitude')
            longitude = location.get('longitude')

            if not latitude:
                raise exceptions.ValidationError({
                    'latitude': _('Latitude is required')
                })

            if not longitude:
                raise exceptions.ValidationError({
                    'longitude': _('Longitude is required')
                })

            timesheet_id = location.get('timesheet_id')
            name = location.get('name')

            if not timesheet_id:
                now = utc_now()
                timesheet = TimeSheet.objects.filter(
                    job_offer__candidate_contact=instance,
                    shift_started_at__lte=now,
                    shift_ended_at__gte=now,
                    going_to_work_confirmation=True
                ).first()

                timesheet_id = timesheet and timesheet.pk
            log_at = location.get('log_at')
            location_logger.log_instance_location(instance, float(latitude), float(longitude), timesheet_id, name, log_at)

        return Response({'status': 'success'})

    @action(methods=['get'], detail=True)
    def history(self, request, *args, **kwargs):
        instance = self.get_object()

        limit = int(request.query_params.get('limit', 10))
        offset = int(request.query_params.get('offset', 0))
        page = offset // limit + 1
        timesheet_id = request.query_params.get('timesheet')

        data = location_logger.fetch_location_history(
            instance, page_num=page, page_size=limit, timesheet_id=timesheet_id
        )

        return Response(data)

    @action(methods=['get'], detail=False)
    def candidates_location(self, request, *args, **kwargs):
        job_id = request.query_params.get('job_id')
        if not job_id:
            data = location_logger.fetch_location_candidates(return_all=True)
            return Response(data)
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            exceptions.ValidationError({'job': _('Cannot find job')})

        timesheets = list(TimeSheet.objects.filter(
            Q(shift_ended_at__gte=utc_now() - timedelta(hours=8)) | Q(shift_ended_at=None),
            ~Q(shift_started_at=None),
            job_offer_id__in=job.get_job_offers().values('id'),
            going_to_work_confirmation=True,
        ).values_list('id', flat=True))

        data = location_logger.fetch_location_candidates(
            instances=timesheets,
        )
        return Response(data)


class SuperannuationFundViewset(BaseApiViewset):

    http_method_names = ['get']
    permission_classes = [drf_permissions.AllowAny]


class VisaTypeViewset(BaseApiViewset):
    serializer_class = serializers.VisaTypeSerializer
    search_fields = ['name']

    def get_queryset(self):
        country = self.request.user.company.country
        visa_country_rel = CountryVisaTypeRelation.objects.filter(country=country)
        return VisaType.objects.filter(visa_types__in=visa_country_rel)


class FormalityViewset(BaseApiViewset):
    http_method_names = ['get', 'post', 'delete']

    def perform_create(self, serializer):
        candidate_contact = self.request.data.get('candidate_contact')
        country = self.request.data.get('country')
        tax_number = self.request.data.get('tax_number', None)
        personal_id = self.request.data.get('personal_id', None)
        # update tax_number
        if tax_number:
            Formality.objects.update_or_create(candidate_contact_id=candidate_contact, country_id=country,
                                               defaults={'tax_number': tax_number})
        # update personal_id
        if personal_id:
            Formality.objects.update_or_create(candidate_contact_id=candidate_contact, country_id=country,
                                               defaults={'personal_id': personal_id})
