from cities_light.loading import get_model
from django.apps import apps
from django.conf import settings
from django.db.models import Q
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.validators import validate_email
from django.utils.translation import ugettext_lazy as _

from phonenumber_field import phonenumber
from rest_framework import viewsets, exceptions, status, fields
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from .. import models, mixins
from ..decorators import get_model_workflow_functions
from ..service import factory
from ..utils.companies import get_master_companies_by_contact, get_site_master_company
from ..utils.user import get_default_company
from ..workflow import WorkflowProcess

from . import permissions, serializers

from r3sourcer.apps.core.api.mixins import GoogleAddressMixin
from r3sourcer.apps.core.tasks import send_contact_verify_sms, send_contact_verify_email
from r3sourcer.apps.core.utils.form_builder import StorageHelper
from r3sourcer.apps.core.utils.address import parse_google_address


class BaseViewsetMixin():
    related_setting = None

    permission_classes = ()

    list_fields = None

    def __init__(self, *args, **kwargs):
        if 'options' not in self.http_method_names:
            self.http_method_names = list(self.http_method_names) + ['options']

        super(BaseViewsetMixin, self).__init__(*args, **kwargs)

    def get_list_fields(self, request):
        return self.list_fields or []

    def dispatch(self, request, *args, **kwargs):
        self.list_fields = request.GET.getlist('fields', [])
        self.related_setting = request.GET.get('related')

        return super(BaseViewsetMixin, self).dispatch(request, *args, **kwargs)

    def get_serializer_context(self):
        context = super(BaseViewsetMixin, self).get_serializer_context()
        if self.related_setting is not None:
            context['related_setting'] = self.related_setting

        return context


class BaseApiViewset(BaseViewsetMixin, viewsets.ModelViewSet):

    _exclude_data = {'__str__'}
    exclude_empty = False

    picture_fields = {'picture', 'logo'}

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        fields = self.get_list_fields(request)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, fields=fields)
            data = self.process_response_data(serializer.data, page)
            return self.get_paginated_response(data)

        serializer = self.get_serializer(queryset, many=True, fields=fields)
        data = self.process_response_data(serializer.data, queryset)
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        fields = self.get_list_fields(request)

        instance = self.get_object()
        serializer = self.get_serializer(instance, fields=fields)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        data = self.prepare_related_data(request.data, is_create=True)
        data = self.clean_request_data(data)

        return self.create_from_data(data, *args, **kwargs)

    def create_from_data(self, data, *args, **kwargs):
        is_response = kwargs.pop('is_response', True)

        many = isinstance(data, list)

        serializer = self.get_serializer(data=data, many=many)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        if is_response:
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            return serializer

    def update(self, request, *args, **kwargs):
        data = self.prepare_related_data(request.data)
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def process_response_data(self, data, queryset=None):
        return data

    def prepare_related_data(self, data, is_create=False):
        return self._prepare_internal_data(data, is_create=False)

    def _prepare_internal_data(self, data, is_create=False):
        res = {}

        if isinstance(data, list):
            return [self._prepare_internal_data(item) if isinstance(item, dict) else item for item in data]

        for key, val in data.items():
            is_empty = val == '' or val is fields.empty
            if key in self._exclude_data or (self.exclude_empty and is_empty and (key != 'id' or len(data) > 1)):
                continue

            if isinstance(val, dict):
                val = {k: v for k, v in val.items() if k not in self.picture_fields}

                res[key] = self._prepare_internal_data(val)
            elif isinstance(val, list):
                res[key] = self._prepare_internal_data(val)

                # res[key] = [self._prepare_internal_data(item) if isinstance(item, dict) else item for item in val]
            else:
                res[key] = val

        return res['id'] if len(res) == 1 and 'id' in res else res

    def clean_request_data(self, data):
        if isinstance(data, list):
            return [self.clean_request_data(item) for item in data]

        return {
            k: v for k, v in data.items() if v is not None
        }


class ContactViewset(GoogleAddressMixin, BaseApiViewset):

    @action(methods=['get'], detail=False)
    def validate(self, request, *args, **kwargs):
        email = request.GET.get('email')
        phone = request.GET.get('phone')

        if email is not None:
            try:
                validate_email(email)
                message = _('Email is valid')
            except ValidationError as e:
                raise exceptions.ValidationError({
                    'valid': False,
                    'message': e.message
                })
        elif phone is not None:
            phone = '+{}'.format(phone) if '+' not in phone else phone
            phone_number = phonenumber.to_python(phone)
            if not phone_number or not phone_number.is_valid():
                raise exceptions.ValidationError({
                    'valid': False,
                    'message': _('Enter a valid Phone Number')
                })
            else:
                message = _('Phone Number is valid')
        else:
            raise exceptions.ValidationError({
                'valid': False,
                'message': _('Please specify Email or Phone Number')
            })

        return Response({
            'status': 'success',
            'data': {
                'valid': True,
                'message': message
            }
        })

    @action(methods=['put'], detail=True)
    def password(self, request, pk=None, *args, **kwargs):
        serializer = serializers.ContactPasswordSerializer(
            data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            'status': 'success',
            'message': _('Password changed successfully')
        })

    @action(methods=['get'], detail=True)
    def verify_email(self, request, *args, **kwargs):
        contact = self.get_object()
        contact.email_verified = True
        contact.save(update_fields=['email_verified'])

        return Response({
            'status': 'success',
            'message': _('Email verified!')
        })

    def prepare_related_data(self, data, is_create=False):
        data = super().prepare_related_data(data, is_create)

        if self.request.query_params.get('candidate') and not data.get('birthday'):
            raise exceptions.ValidationError({'birthday': _('Birthday is required')})

        return data

    def perform_create(self, serializer):
        instance = serializer.save()

        manager_id = self.request.user.contact

        send_contact_verify_sms.apply_async(args=(instance.id, manager_id.id), countdown=10)
        send_contact_verify_email.apply_async(args=(instance.id, manager_id.id), countdown=10)


class CompanyViewset(BaseApiViewset):

    http_method_names = ['post', 'put', 'get', 'delete', 'options']
    action_map = {
        'put': 'partial_update'
    }

    def process_response_data(self, data, queryset=None):
        if 'country' in self.request.GET or \
                'business_id' in self.request.GET:
            if isinstance(data, dict) and data.get('count') > 0:
                data.update({
                    'message': _('Company already exists')
                })
            elif isinstance(data, list) and len(data) > 0:
                data = {
                    'message': _('Company already exists'),
                    'results': data
                }
        return data

    def perform_update(self, serializer):
        instance = self.get_object()

        errors = []
        if not instance.company_addresses.filter(active=True).exists():
            errors.append(_('At least one address must be active'))

        if instance.company_addresses.filter(active=True, primary_contact__isnull=True).exists():
            errors.append(_('All active addresses must have primary contact'))

        if errors:
            raise exceptions.ValidationError({'non_field_errors': errors})

        instance = serializer.save()

        if instance.type == models.Company.COMPANY_TYPES.master:
            return

        master_company = self.request.data.get('master_company')
        master_company = master_company.get('id') if isinstance(master_company, dict) else master_company
        primary_contact = self.request.data.get('primary_contact')
        primary_contact = primary_contact.get('id') if isinstance(primary_contact, dict) else primary_contact
        company_rel = instance.regular_companies.first()

        if master_company:
            master_company_obj = models.Company.objects.get(id=master_company)
            if primary_contact:
                primary_contact_obj = models.CompanyContact.objects.get(id=primary_contact)
            else:
                primary_contact_obj = None

            if not company_rel and instance.type != models.Company.COMPANY_TYPES.master:
                models.CompanyRel.objects.create(
                    master_company=master_company_obj,
                    regular_company=instance,
                    primary_contact=primary_contact_obj
                )
            else:
                company_rel.master_company = master_company_obj
                company_rel.primary_contact = primary_contact_obj
                company_rel.save()

    def create(self, request, *args, **kwargs):
        data = self.prepare_related_data(request.data)
        data = self.clean_request_data(data)

        invoice_rule_data = data.pop('invoice_rule', None)
        if invoice_rule_data:
            invoice_rule_data.pop('id')

            # check Invoice Rule fields for new Company
            invoice_rule_serializer = serializers.InvoiceRuleSerializer(data=invoice_rule_data)
            if not invoice_rule_serializer.is_valid():
                errors = invoice_rule_serializer.errors
                errors.pop('company', None)
                if errors:
                    raise exceptions.ValidationError(errors)

        # create Company
        kwargs['is_response'] = False
        instance_serializer = self.create_from_data(data, *args, **kwargs)

        if invoice_rule_data:
            # update Invoice Rule object
            invoice_rule_data['company'] = instance_serializer.instance.id
            invoice_rule_instance = instance_serializer.instance.invoice_rules.first()
            invoice_rule_serializer = serializers.InvoiceRuleSerializer(
                instance=invoice_rule_instance, data=invoice_rule_data, partial=True
            )
            invoice_rule_serializer.is_valid(raise_exception=True)
            invoice_rule_serializer.save()

        master_company = get_site_master_company(request=request, user=request.user).id
        primary_contact = request.user.contact.company_contact.first().id
        models.CompanyRel.objects.create(
            master_company_id=master_company,
            regular_company=instance_serializer.instance,
            primary_contact_id=primary_contact
        )

        headers = self.get_success_headers(instance_serializer.data)
        return Response(instance_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_destroy(self, instance):
        company_rels = instance.regular_companies.values_list('id', flat=True)
        content_type = ContentType.objects.get_for_model(models.CompanyRel)
        exclude_states = models.WorkflowObject.objects.filter(
            state__number__gt=10, state__workflow__model=content_type, active=True, object_id__in=company_rels
        ).values_list('object_id', flat=True)
        states = models.WorkflowObject.objects.filter(
            state__number__in=[10, 0], state__workflow__model=content_type, active=True, object_id__in=company_rels
        ).exclude(
            object_id__in=set(exclude_states)
        ).distinct('object_id').values_list('object_id', flat=True)

        relations_in_state = states.count() == instance.regular_companies.count()

        if instance.relationships.exists() or instance.jobsites_regular.exists() or not relations_in_state:
            raise ValidationError(_('Cannot delete'))

        instance.candidate_rels.delete()

        super().perform_destroy(instance)


class CompanyContactViewset(BaseApiViewset):

    def get_serializer_context(self):
        context = super(CompanyContactViewset, self).get_serializer_context()
        user = context['request'].user
        if user and user.is_authenticated:
            context['approved_by_staff'] = self.is_approved_by_staff(user)
            context['approved_by_primary_contact'] = self.is_approved_by_primary_contact(user)
        return context

    def is_approved_by_staff(self, user):
        return models.CompanyContactRelationship.objects.filter(
            company__type=models.Company.COMPANY_TYPES.master,
            company_contact__contact__user=user).exists()

    def is_approved_by_primary_contact(self, user):
        return models.CompanyRel.objects.filter(primary_contact__contact__user=user).exists()

    def get_object(self):
        obj = super().get_object()

        rel = obj.relationships.first()

        if rel:
            obj.active = rel.active
            obj.termination_date = rel.termination_date

        return obj

    def perform_destroy(self, instance):
        has_jobsites = instance.managed_jobsites.exists() or instance.jobsites.exists()
        has_jobs = (
            instance.provider_representative_jobs.exists() or instance.customer_representative_jobs.exists()
        )

        if has_jobs or has_jobsites or instance.supervised_time_sheets.exists():
            raise ValidationError({'non_field_errors': _('Cannot delete')})

        rels = instance.relationships.all()
        models.Role.objects.filter(company_contact_rel__in=rels).delete()
        rels.delete()

        super().perform_destroy(instance)

    def prepare_related_data(self, data, is_create=False):
        if is_create and not data.get('contact'):
            data['contact'] = fields.empty

        return self._prepare_internal_data(data, is_create=is_create)

    @action(methods=['post'], detail=False)
    def register(self, request, *args, **kwargs):
        serializer = serializers.CompanyContactRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        phone_number = instance.contact.phone_mobile
        if phone_number:
            login_service = factory.get_instance('login')
            login_service.send_login_sms(instance.contact,
                                         '/#/registration/password')

        serializer = serializers.CompanyContactSerializer(instance)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data,
                        status=status.HTTP_201_CREATED,
                        headers=headers)

    @action(methods=['post'], detail=False)
    def sendsms(self, request, *args, **kwargs):
        id_list = request.data

        if not id_list or not isinstance(id_list, list):
            raise exceptions.ParseError(_('You should select Company addresses'))

        phone_numbers = self.model.objects.filter(
            id__in=id_list, contact__phone_mobile__isnull=False
        ).values_list(
            'contact__phone_mobile', flat=True
        ).distinct()

        return Response({
            'status': 'success',
            'phone_number': phone_numbers,
            'message': _('Phones numbers was selected'),
        })


class SiteViewset(BaseApiViewset):

    permission_classes = (permissions.SitePermissions,)
    filter_backends = (permissions.SiteClosestCompanyFilterBackend,)


class NavigationViewset(BaseApiViewset):

    def get_queryset(self):
        role_id = self.request.query_params.get('role', None)

        try:
            role = models.Role.objects.get(id=role_id)
            access_level = role.name
        except Exception:
            access_level = self.request.user.access_level

        return models.ExtranetNavigation.objects.filter(parent=None, access_level=access_level)


class CompanyAddressViewset(GoogleAddressMixin, BaseApiViewset):

    def get_queryset(self):
        current_site = get_current_site(self.request)
        master_type = models.Company.COMPANY_TYPES.master

        site_companies = models.SiteCompany.objects.filter(
            site=current_site,
            company__type=master_type,
        ).values_list('company_id', flat=True)
        if not site_companies.exists():
            return models.CompanyAddress.objects.none()
        else:
            return models.CompanyAddress.objects.filter(
                Q(company__in=site_companies) |
                Q(company__regular_companies__master_company__in=site_companies)
            ).distinct()

    def prepare_related_data(self, data, is_create=False):
        data = super().prepare_related_data(data, is_create)

        if is_create and not data.get('active'):
            data['active'] = True

        if not data.get('primary_contact'):
            raise exceptions.ValidationError({'primary_contact': _('Primary contact must be set')})

        return data

    def perform_destroy(self, instance):
        if models.CompanyAddress.objects.filter(company=instance.company).count() == 1:
            company_rel = instance.company.regular_companies.last()
            if company_rel and company_rel.is_allowed(80):
                company_rel.create_state(80, _('Company has no active address!'))

        super().perform_destroy(instance)

    @action(methods=['post'], detail=False)
    def delete(self, request, *args, **kwargs):
        ids = request.data

        if not ids:
            raise exceptions.ParseError(_('Objects not selected'))

        return Response({
            'status': 'success',
            'message': _('Deleted successfully'),
        })

    @action(methods=['post'], detail=False)
    def sendsms(self, request, *args, **kwargs):
        id_list = request.data

        if not id_list or not isinstance(id_list, list):
            raise exceptions.ParseError(_('You should select Company addresses'))

        phone_numbers = set(models.CompanyAddress.objects.filter(
            id__in=id_list, primary_contact__contact__phone_mobile__isnull=False).values_list(
            'primary_contact__contact__phone_mobile', flat=True))

        return Response({
            'status': 'success',
            'phone_number': phone_numbers,
            'message': _('Phones numbers was selected'),
        })


class AppsList(ViewSet):

    def list(self, request, format=None, **kwargs):
        """
        Return a list of applications
        """
        return Response([app.replace('r3sourcer.apps.', '') for app in settings.INSTALLED_APPS])


class ModelsList(ViewSet):

    def list(self, request, format=None, *args, **kwargs):
        """
        Return a list of all models by application name.
        """
        app_name = request.query_params.get("app_name", None)
        if app_name:
            models = [model._meta.model_name
                      for model in apps.get_app_config(app_name).get_models()]
            return Response(models)
        return Response(status=status.HTTP_400_BAD_REQUEST)


class FunctionsList(ViewSet):

    def list(self, request, format=None, *args, **kwargs):
        """
        Return a list of functions available for workflow by app_name
        and model_name
        """
        app_name = request.query_params.get("app_name", None)
        model_name = request.query_params.get("model_name", None)

        if app_name and model_name:
            try:
                model = get_model(app_name, model_name)
            except LookupError:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            else:
                functions = get_model_workflow_functions(model)
                return Response(functions)
        return Response(status=status.HTTP_400_BAD_REQUEST)


class WorkflowNodeViewset(BaseApiViewset):

    def _get_target(self, model_name, object_id):
        try:
            model_class = apps.get_model(model_name)
            target_object = model_class.objects.get(id=object_id)
        except ObjectDoesNotExist:
            raise exceptions.NotFound(_('Object does not exists'))

        required_mixins = (WorkflowProcess, mixins.CompanyLookupMixin)
        if not isinstance(target_object, required_mixins):
            raise exceptions.NotFound(_('Object does not have workflow'))

        return target_object

    @action(methods=['get'], detail=False)
    def timeline(self, request, *args, **kwargs):
        model = request.query_params.get('model')
        object_id = request.query_params.get('object_id')
        company = request.query_params.get('company')

        if not model or not object_id:
            raise exceptions.NotFound(_('Workflow Nodes not found'))

        target_object = self._get_target(model, object_id)

        try:
            company = models.Company.objects.get(id=company)
        except models.Company.DoesNotExist:
            company = target_object.get_closest_company()

        try:
            model_ct = ContentType.objects.get_by_natural_key(
                *model.split('.')
            )
            workflow = models.Workflow.objects.get(model=model_ct)
        except (IndexError, models.Workflow.DoesNotExist):
            workflow = None

        if workflow is None:
            raise exceptions.NotFound(_('Workflow not found for model'))

        nodes = models.WorkflowNode.get_company_nodes(company, workflow).filter(parent__isnull=True)

        serializer = serializers.WorkflowTimelineSerializer(
            nodes, target=target_object, many=True
        )

        return Response(serializer.data, status=status.HTTP_200_OK)


class CompanyWorkflowNodeViewset(BaseApiViewset):

    def perform_create(self, serializer):
        company_node = models.CompanyWorkflowNode.objects.filter(
            company=serializer.validated_data['company'],
            workflow_node=serializer.validated_data['workflow_node']
        ).first()

        if company_node is not None:
            company_node.active = True
            company_node.save()
        else:
            serializer.save()

    def perform_destroy(self, instance):
        instance.active = False
        instance.save()


class UserDashboardModuleViewSet(BaseApiViewset):

    CAN_NOT_CREATE_MODULE_ERROR = _("You should be CompanyContact to creating module")

    def get_queryset(self):
        if self.request.user.is_authenticated():
            return models.UserDashboardModule.objects.filter(
                company_contact__contact__user_id=self.request.user.id
            )
        return models.DashboardModule.objects.none()

    def perform_create(self, serializer):

        company_contact = self.request.user.contact.company_contact.last()
        if company_contact is None:
            raise exceptions.APIException(self.CAN_NOT_CREATE_MODULE_ERROR)

        has_create_perm = self.request.user.has_perm(
            'can_use_module', obj=serializer.validated_data['dashboard_module']
        )
        if not has_create_perm:
            raise exceptions.PermissionDenied
        serializer.save(company_contact=company_contact)


class DashboardModuleViewSet(BaseApiViewset):

    def create(self, request, *args, **kwargs):
        if not request.user.has_perm('core.add_dashboardmodule'):
            raise exceptions.PermissionDenied
        return super(DashboardModuleViewSet, self).create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.has_perm('core.delete_dashboardmodule'):
            raise exceptions.PermissionDenied
        return super(DashboardModuleViewSet, self).destroy(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super(DashboardModuleViewSet, self).get_queryset().prefetch_related('content_type')
        result = [
            obj.id
            for obj in queryset
            if self.request.user.has_perm('can_use_module', obj)
        ]
        return queryset.filter(id__in=result)


class FormBuilderViewSet(BaseApiViewset):

    permission_classes = (permissions.ReadonlyOrIsSuperUser,)
    serializer_class = serializers.FormBuilderSerializer


class ContentTypeViewSet(BaseApiViewset):

    permission_classes = (permissions.ReadOnly,)


class FormViewSet(BaseApiViewset):

    serializer_class = serializers.FormSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        if self.request.user.is_superuser:
            return models.Form.objects.all()
        companies = get_master_companies_by_contact(self.request.user.contact)
        return models.Form.objects.filter(
            Q(company__isnull=True) |
            Q(company__in=companies)
        )

    def create(self, request, *args, **kwargs):
        data = self.prepare_related_data(request.data)

        companies = get_master_companies_by_contact(self.request.user.contact)
        if len(companies) > 0:
            data['company'] = companies[0].id
        else:
            data['company'] = get_default_company().id

        data = self.clean_request_data(data)

        return self.create_from_data(data, *args, **kwargs)

    @action(methods=['get'], detail=True)
    def render(self, request, pk, *args, **kwargs):
        fields = self.get_list_fields(request)
        instance = self.get_object()
        serializer = serializers.FormRenderSerializer(instance, fields=fields)

        return Response(serializer.data)

    @action(methods=['post'], detail=True)
    def submit(self, request, pk, *args, **kwargs):
        form_obj = self.get_object()
        data = models.Form.parse_api_data(request.data)
        form = form_obj.get_form_class()(data=data, files=request.data)

        if not form.is_valid():
            raise exceptions.ValidationError(form.errors)

        form_storage_data = models.Form.parse_data_to_storage(form.cleaned_data)
        form_storage_data, errors = form_obj.get_data(form_storage_data)

        if errors:
            raise exceptions.ValidationError(errors)

        storage_helper = StorageHelper(form_obj.content_type.model_class(), form_storage_data)
        storage_helper.process_fields()

        if not storage_helper.validate():
            raise exceptions.ValidationError(storage_helper.errors)

        storage_helper.create_instance()

        return Response({'message': form_obj.submit_message}, status=status.HTTP_201_CREATED)


class CitiesLightViewSet(BaseApiViewset):

    def get_queryset(self):
        qs = super().get_queryset()

        return qs.order_by('name')


class AddressViewset(GoogleAddressMixin, BaseApiViewset):
    root_address = True

    @action(methods=['post'], detail=False)
    def parse(self, request, *args, **kwargs):
        try:
            address_data = request.data
            data = parse_google_address(address_data)
        except Exception as e:
            raise exceptions.ValidationError(_('Address is invalid!'))

        return Response(data)


class CompanyContactRelationshipViewset(BaseApiViewset):

    def perform_destroy(self, instance):
        company_contact = instance.company_contact
        has_jobsites = company_contact.managed_jobsites.exists() or company_contact.jobsites.exists()
        has_jobs = (
            company_contact.provider_representative_jobs.exists() or
            company_contact.customer_representative_jobs.exists()
        )

        if has_jobs or has_jobsites or company_contact.supervised_time_sheets.exists():
            raise ValidationError({'non_field_errors': _('Cannot delete')})

        models.Role.objects.filter(company_contact_rel=instance).delete()

        super().perform_destroy(instance)

        company_contact.delete()
