from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django_filters import (
    CharFilter, UUIDFilter, NumberFilter, BooleanFilter, ModelChoiceFilter,
)
from django_filters.rest_framework import FilterSet
from rest_framework.filters import OrderingFilter

from ..models import (
    Company, CompanyLocalization, CompanyAddress, CompanyRel, WorkflowObject,
    WorkflowNode, DashboardModule, CompanyContact, FormField, CompanyContactRelationship
)
from ..utils.user import get_default_company


class CompanyFilter(FilterSet):
    name = CharFilter(name='name', method='filter_name')
    country = CharFilter(name='addresses', method='filter_country')
    state = UUIDFilter(method='filter_state')
    status = NumberFilter(method='filter_status')
    portfolio_manager = UUIDFilter(method='filter_portfolio_manager')
    regular_company = UUIDFilter(method='filter_regular_company')

    class Meta:
        model = Company
        fields = ['name', 'business_id', 'country', 'type', 'id']

    def filter_name(self, queryset, name, value):
        return queryset.filter(
            name__icontains=value,
        )

    def filter_country(self, queryset, name, value):
        return queryset.filter(
            company_addresses__hq=True,
            company_addresses__address__country=value
        )

    def filter_state(self, queryset, name, value):
        return queryset.filter(
            company_addresses__hq=True,
            company_addresses__address__state=value
        )

    def filter_status(self, queryset, name, value):
        objects = self._fetch_workflow_objects(value)
        return queryset.filter(
            Q(regular_companies__id__in=objects) |
            Q(master_companies__id__in=objects)
        )

    def filter_regular_company(self, queryset, name, value):
        return queryset.filter(master_companies__regular_company=value)

    def filter_portfolio_manager(self, queryset, name, value):
        return queryset.filter(
            Q(regular_companies__primary_contact=value) |
            Q(master_companies__primary_contact=value)
        )

    def _fetch_workflow_objects(self, value):  # pragma: no cover
        content_type = ContentType.objects.get_for_model(CompanyRel)
        objects = WorkflowObject.objects.filter(
            state__number=value,
            state__workflow__model=content_type,
            active=True,
        ).distinct('object_id').values_list('object_id', flat=True)

        return objects


class CompanyLocalizationFilter(FilterSet):
    field_name = CharFilter(name='field_name', lookup_expr='icontains')
    country = CharFilter(name='country', method='filter_country')

    class Meta:
        model = CompanyLocalization
        fields = ['field_name', 'country']

    def filter_country(self, queryset, name, value):
        qs = queryset.filter(
            country=value
        )

        if qs.exists():
            return qs
        return queryset.filter(country__isnull=True)


class CompanyAddressFilter(FilterSet):
    portfolio_manager = UUIDFilter(method='filter_portfolio_manager')
    state = NumberFilter(method='filter_state')

    class Meta:
        model = CompanyAddress
        fields = ['portfolio_manager', 'company']

    def filter_portfolio_manager(self, queryset, name, value):
        return queryset.filter(
            Q(company__regular_companies__primary_contact=value) |
            Q(company__master_companies__primary_contact=value)
        )

    def _fetch_workflow_objects(self, value):  # pragma: no cover
        content_type = ContentType.objects.get_for_model(CompanyRel)
        objects = WorkflowObject.objects.filter(
            state__number=value,
            state__workflow__model=content_type,
            active=True,
        ).distinct('object_id').values_list('object_id', flat=True)

        return objects

    def filter_state(self, queryset, name, value):
        objects = self._fetch_workflow_objects(value)
        return queryset.filter(
            Q(company__regular_companies__id__in=objects) |
            Q(company__master_companies__id__in=objects)
        )


class ApiOrderingFilter(OrderingFilter):

    def get_default_valid_fields(self, queryset, view, context={}):
        if hasattr(view, 'endpoint'):
            endpoint = view.endpoint
            fields = endpoint.get_metadata_fields(False)
            return set([
                (field, field)
                for field in fields if '__str__' not in field
            ])

        return super(ApiOrderingFilter, self).get_default_valid_fields(
            queryset, view, context
        )

    def remove_invalid_fields(self, queryset, fields, view, request):
        valid_fields = [item[0] for item in self.get_valid_fields(queryset, view, {'request': request})]
        return [term.replace('.', '__') for term in fields if term.lstrip('-') in valid_fields]


class WorkflowNodeFilter(FilterSet):
    default = BooleanFilter(method='filter_default')
    company = ModelChoiceFilter(
        queryset=Company.objects,
        method='filter_company'
    )

    class Meta:
        model = WorkflowNode
        fields = ['workflow', 'company', 'default']

    def filter_default(self, queryset, name, value):
        if value:
            return queryset.filter(
                company=get_default_company()
            )
        return queryset

    def filter_company(self, queryset, name, value):
        if not value:
            return queryset

        company_nodes = WorkflowNode.get_company_nodes(
            value, nodes=queryset
        )

        return company_nodes


class DashboardModuleFilter(FilterSet):

    model = CharFilter(name='content_type', lookup_expr='model__icontains')
    app_label = CharFilter(name='content_type', lookup_expr='app_label__icontains')

    class Meta:
        model = DashboardModule
        fields = ('model', 'app_label', 'is_active')


class CompanyContactFilter(FilterSet):
    company = UUIDFilter(method='filter_company')
    manager = UUIDFilter(method='filter_manager')
    is_manager = BooleanFilter(method='filter_is_manager')

    class Meta:
        model = CompanyContact
        fields = ['job_title']

    def filter_company(self, queryset, name, value):
        return queryset.filter(
            relationships__company_id=value
        )

    def filter_manager(self, queryset, name, value):
        return queryset.filter(
            relationships__company__manager_id=value
        )

    def filter_is_manager(self, queryset, name, value):
        return queryset.filter(
            companies__isnull=False,
        )


class CompanyContactRelationshipFilter(FilterSet):
    company = UUIDFilter(method='filter_company')

    class Meta:
        model = CompanyContactRelationship
        fields = ['company']

    def filter_company(self, queryset, name, value):
        return queryset.filter(
            company_id=value
        )


class FormFieldFilter(FilterSet):

    class Meta:
        model = FormField
        fields = ('group',)


class WorkflowObjectFilter(FilterSet):

    class Meta:
        model = WorkflowObject
        fields = ('object_id',)
