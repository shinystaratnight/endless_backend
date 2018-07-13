from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django_filters import CharFilter, UUIDFilter, NumberFilter, BooleanFilter, ModelChoiceFilter
from django_filters.rest_framework import FilterSet
from rest_framework.filters import OrderingFilter

from r3sourcer.apps.core import models
from r3sourcer.apps.core_adapter.filters import DateRangeFilter
from r3sourcer.apps.core.models.constants import CANDIDATE
from r3sourcer.apps.core.utils.user import get_default_company
from r3sourcer.apps.core.utils.companies import get_site_master_company


class CompanyFilter(FilterSet):
    name = CharFilter(name='name', method='filter_name')
    country = CharFilter(name='addresses', method='filter_country')
    state = UUIDFilter(method='filter_state')
    status = NumberFilter(method='filter_status')
    portfolio_manager = UUIDFilter(method='filter_portfolio_manager')
    regular_company = UUIDFilter(method='filter_regular_company')
    current = BooleanFilter(method='filter_current')
    has_industry = BooleanFilter(method='filter_has_industry')

    class Meta:
        model = models.Company
        fields = ['name', 'business_id', 'country', 'type', 'id', 'approved_credit_limit']

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
        ).distinct()

    def filter_regular_company(self, queryset, name, value):
        return queryset.filter(master_companies__regular_company=value)

    def filter_portfolio_manager(self, queryset, name, value):
        return queryset.filter(
            Q(regular_companies__primary_contact=value) |
            Q(master_companies__primary_contact=value)
        ).distinct()

    def _fetch_workflow_objects(self, value):  # pragma: no cover
        content_type = ContentType.objects.get_for_model(models.CompanyRel)
        exclude_values = models.WorkflowObject.objects.filter(
            state__number__gt=value, state__workflow__model=content_type, active=True
        ).values_list('object_id', flat=True)

        return models.WorkflowObject.objects.filter(
            state__number=value, state__workflow__model=content_type, active=True,
        ).exclude(
            object_id__in=set(exclude_values)
        ).distinct('object_id').values_list('object_id', flat=True)

    def filter_current(self, queryset, name, value):
        if value:
            company = get_site_master_company() or get_default_company()
            return queryset.filter(id=company.id)
        return queryset

    def filter_has_industry(self, queryset, name, value):
        if value:
            return queryset.filter(industry__isnull=False).distinct()
        return queryset


class CompanyLocalizationFilter(FilterSet):
    field_name = CharFilter(name='field_name', lookup_expr='icontains')
    country = CharFilter(name='country', method='filter_country')

    class Meta:
        model = models.CompanyLocalization
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
    updated_at = DateRangeFilter()

    class Meta:
        model = models.CompanyAddress
        fields = ['portfolio_manager', 'company', 'primary_contact', 'updated_at']

    def filter_portfolio_manager(self, queryset, name, value):
        return queryset.filter(
            Q(company__regular_companies__primary_contact=value) |
            Q(company__master_companies__primary_contact=value)
        )


class ApiOrderingFilter(OrderingFilter):

    def remove_invalid_fields(self, queryset, fields, view, request):
        valid_fields = [item[0] for item in self.get_valid_fields(queryset, view, {'request': request})]
        return [term.replace('.', '__') for term in fields if term.lstrip('-') in valid_fields]


class WorkflowNodeFilter(FilterSet):
    company = ModelChoiceFilter(queryset=models.Company.objects, method='filter_company')
    system = BooleanFilter(method='filter_system')
    workflow = UUIDFilter(method='filter_workflow')

    _company = None
    _workflow = None

    class Meta:
        model = models.WorkflowNode
        fields = ['workflow', 'workflow__model', 'parent']

    def filter_workflow(self, queryset, name, value):
        self._workflow = value

        return queryset.filter(workflow=value)

    def filter_company(self, queryset, name, value):
        if not value:
            return queryset

        self._company = value

        return queryset.filter(
            company_workflow_nodes__company=value, active=True, company_workflow_nodes__active=True,
            parent__isnull=True
        ).distinct()

    def filter_system(self, queryset, name, value):
        if not value:
            return queryset

        workflow_qry = Q(workflow=self._workflow) if self._workflow else Q()
        site_company = get_site_master_company()
        system_nodes = models.WorkflowNode.objects.filter(
            workflow_qry, company_workflow_nodes__company=site_company, active=True
        ).distinct()

        if self._company:
            system_nodes_exclude = models.WorkflowNode.objects.filter(
                company_workflow_nodes__company=self._company,
                company_workflow_nodes__active=True
            ).values_list('id', flat=True)
            system_nodes = models.WorkflowNode.objects.filter(
                Q(company_workflow_nodes__company=self._company, active=True) |
                Q(id__in=system_nodes.values_list('id', flat=True)),
                workflow_qry
            ).exclude(id__in=system_nodes_exclude).distinct()

        return system_nodes


class CompanyWorkflowNodeFilter(FilterSet):

    only_parent = BooleanFilter(method='filter_only_parent')

    class Meta:
        model = models.CompanyWorkflowNode
        fields = ['company', 'active', 'workflow_node__workflow', 'workflow_node__parent']

    def filter_only_parent(self, queryset, name, value):
        return queryset.filter(workflow_node__parent__isnull=value)


class DashboardModuleFilter(FilterSet):

    model = CharFilter(name='content_type', lookup_expr='model__icontains')
    app_label = CharFilter(name='content_type', lookup_expr='app_label__icontains')

    class Meta:
        model = models.DashboardModule
        fields = ('model', 'app_label', 'is_active')


class CompanyContactFilter(FilterSet):
    company = UUIDFilter(method='filter_company')
    manager = UUIDFilter(method='filter_manager')
    is_manager = BooleanFilter(method='filter_is_manager')
    jobsites = UUIDFilter(method='filter_jobsite')
    customer_company = UUIDFilter(method='filter_customer_company', distinct=True)
    master_company = CharFilter(method='filter_master_company', distinct=True)

    class Meta:
        model = models.CompanyContact
        fields = ['id', 'job_title']

    def filter_company(self, queryset, name, value):
        return queryset.filter(relationships__company_id=value, relationships__active=True)

    def filter_manager(self, queryset, name, value):
        return queryset.filter(
            relationships__company__manager_id=value
        )

    def filter_is_manager(self, queryset, name, value):
        return queryset.filter(
            companies__isnull=False,
        )

    def filter_jobsite(self, queryset, name, value):
        return queryset.filter(jobsites=value)

    def filter_customer_company(self, queryset, name, value):
        return queryset.filter(company_accounts__regular_company=value).distinct()

    def filter_master_company(self, queryset, name, value):
        if value == 'current':
            company = get_site_master_company() or get_default_company()
            value = company.id

        return queryset.filter(relationships__company_id=value, relationships__active=True).distinct()


class CompanyContactRelationshipFilter(FilterSet):
    company = UUIDFilter(method='filter_company')
    contact = UUIDFilter(method='filter_contact')

    class Meta:
        model = models.CompanyContactRelationship
        fields = ['company', 'active']

    def filter_company(self, queryset, name, value):
        return queryset.filter(company_id=value)

    def filter_contact(self, queryset, name, value):
        return queryset.filter(company_contact__contact_id=value)


class FormFieldFilter(FilterSet):

    class Meta:
        model = models.FormField
        fields = ('group', )


class WorkflowObjectFilter(FilterSet):

    class Meta:
        model = models.WorkflowObject
        fields = ('object_id', 'active', 'state__workflow__name')


class CountryFilter(FilterSet):

    class Meta:
        model = models.Country
        fields = ('code2',)


class RegionFilter(FilterSet):

    country = UUIDFilter(method='filter_country')

    class Meta:
        model = models.Region
        fields = ('country',)

    def filter_country(self, queryset, name, value):
        return queryset.filter(Q(country_id=value) | Q(country__code2=value))


class CityFilter(FilterSet):

    class Meta:
        model = models.City
        fields = ('country', 'region')


class ContactFilter(FilterSet):

    state = UUIDFilter(method='filter_state')
    contact_type = CharFilter(method='filter_contact_type')
    is_company_contact = BooleanFilter(method='filter_is_company_contact')
    is_candidate_contact = BooleanFilter(method='filter_is_candidate_contact')

    class Meta:
        model = models.Contact
        fields = [
            'state', 'is_company_contact', 'is_candidate_contact', 'phone_mobile_verified', 'email_verified',
            'is_available'
        ]

    def filter_state(self, queryset, name, value):
        return queryset.filter(address__state=value)

    def filter_contact_type(self, queryset, name, value):
        if value == CANDIDATE:
            return queryset.filter(candidate_contacts__isnull=False)
        elif value:
            return queryset.filter(company_contact__role=value)

        return queryset

    def filter_is_company_contact(self, queryset, name, value):
        return queryset.filter(company_contact__isnull=not value)

    def filter_is_candidate_contact(self, queryset, name, value):
        return queryset.filter(candidate_contacts__isnull=not value)


class TagFilter(FilterSet):
    exclude = UUIDFilter(method='exclude_by_candidate')

    class Meta:
        model = models.Tag
        fields = ['exclude', 'confidential']

    def exclude_by_candidate(self, queryset, name, value):
        return queryset.filter(active=True).exclude(tag_rels__candidate_contact_id=value)


class InvoiceFilter(FilterSet):

    class Meta:
        model = models.Invoice
        fields = ['customer_company']


class InvoiceLineFilter(FilterSet):

    class Meta:
        model = models.InvoiceLine
        fields = ['invoice']


class InvoiceRuleFilter(FilterSet):

    class Meta:
        model = models.InvoiceRule
        fields = ['company']


class OrderFilter(FilterSet):

    class Meta:
        model = models.Order
        fields = ['provider_company']


class NoteFilter(FilterSet):

    class Meta:
        model = models.Note
        fields = ['object_id']


class ContactUnavailabilityFilter(FilterSet):

    class Meta:
        model = models.ContactUnavailability
        fields = ['contact']
