from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from rest_framework import status, exceptions, permissions as drf_permissions, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from r3sourcer.apps.acceptance_tests.api.serializers import AcceptanceTestCandidateWorkflowSerializer
from r3sourcer.apps.acceptance_tests.models import AcceptanceTestWorkflowNode
from r3sourcer.apps.core import tasks as core_tasks
from r3sourcer.apps.core.api.viewsets import BaseApiViewset, BaseViewsetMixin
from r3sourcer.apps.core.api.permissions import SiteContactPermissions
from r3sourcer.apps.core.models import Company, InvoiceRule, Workflow
from r3sourcer.apps.core.utils.companies import get_site_master_company
from r3sourcer.apps.logger.main import location_logger

from . import serializers, permissions
from ..models import Subcontractor, CandidateContact, CandidateContactAnonymous, CandidateRel
from ..tasks import buy_candidate


class CandidateContactViewset(BaseApiViewset):

    permission_classes = (permissions.CandidateContactPermissions, SiteContactPermissions)

    def perform_create(self, serializer):
        instance = serializer.save()

        manager_id = self.request.user.contact
        master_company = get_site_master_company(request=self.request)

        if not instance.contact.phone_mobile_verified:
            core_tasks.send_contact_verify_sms.apply_async(args=(instance.contact.id, manager_id.id), countdown=10)

        if not instance.contact.email_verified:
            core_tasks.send_contact_verify_email.apply_async(
                args=(instance.contact.id, manager_id.id, master_company.id), countdown=10
            )

    def perform_destroy(self, instance):
        has_joboffers = instance.job_offers.exists()

        if has_joboffers:
            raise exceptions.ValidationError({'non_field_errors': _('Cannot delete')})

        super().perform_destroy(instance)

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

        phone_numbers = set(self.model.objects.filter(
            id__in=id_list, contact__phone_mobile__isnull=False).values_list(
            'contact__phone_mobile', flat=True))

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
            ).distinct()
        return self._paginate(request, serializers.CandidatePoolSerializer, self.filter_queryset(queryset))

    @action(methods=['post'], detail=True, permission_classes=[SiteContactPermissions])
    def buy(self, request, pk, *args, **kwargs):
        master_company = request.user.contact.get_closest_company().get_closest_master_company()
        candidate_contact = self.get_object()
        company = request.data.get('company')

        is_owner = CandidateRel.objects.filter(
            master_company=master_company, candidate_contact=candidate_contact, owner=True
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
                master_company=company, candidate_contact=candidate_contact, owner=False, active=False
            )

            buy_candidate.apply_async([rel.id], countdown=10)

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
        if closest_company.industry is not None:
            qry |= Q(acceptance_test__acceptance_tests_industries__industry=closest_company.industry)

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


class CandidateLocationViewset(
    BaseViewsetMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):

    queryset = CandidateContact.objects.all()
    serializer_class = serializers.CandidateContactSerializer
    permission_classes = [drf_permissions.IsAuthenticated]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')

        if not latitude:
            raise exceptions.ValidationError({
                'latitude': _('Latitude is required')
            })

        if not longitude:
            raise exceptions.ValidationError({
                'longitude': _('Longitude is required')
            })

        location_logger.log_instance_location(instance, float(latitude), float(longitude))

        return Response({'status': 'success'})

    @action(methods=['get'], detail=True)
    def history(self, request, *args, **kwargs):
        instance = self.get_object()

        limit = request.data.get('limit', 10)
        offset = request.data.get('offset', 0)
        page = offset // limit + 1

        data = location_logger.fetch_location_history(instance, page_num=page, page_size=limit)

        return Response(data)
