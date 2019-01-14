import datetime

from django.db.models import Q
from django.utils import timezone

from django_filters import UUIDFilter, NumberFilter, BooleanFilter, DateFilter
from django_filters.rest_framework import FilterSet

from r3sourcer.apps.core.api.mixins import ActiveStateFilterMixin
from r3sourcer.apps.core.models import Invoice
from r3sourcer.apps.core_adapter.filters import DateRangeFilter
from r3sourcer.apps.hr import models as hr_models


class TimesheetFilter(FilterSet):
    candidate = UUIDFilter(method='filter_candidate')
    approved = BooleanFilter(method='filter_approved')
    company = UUIDFilter('job_offer__shift__date__job__customer_company_id')
    jobsite = UUIDFilter('job_offer__shift__date__job__jobsite_id')
    shift_started_at = DateRangeFilter(distinct=True)

    class Meta:
        model = hr_models.TimeSheet
        fields = ['shift_started_at', 'supervisor']

    def filter_candidate(self, queryset, name, value):
        return queryset.filter(
            job_offer__candidate_contact_id=value
        )

    def filter_company(self, queryset, name, value):
        return queryset.filter(
            job_offer__shift__date__job__customer_company_id=value
        )

    def filter_jobsite(self, queryset, name, value):
        return queryset.filter(
            job_offer__shift__date__job__jobsite_id=value
        )

    def filter_approved(self, queryset, name, value):
        if value:
            qs_approved = self.get_filter_for_approved(self.request.user.contact)
            return queryset.filter(qs_approved)
        qs_unapproved = self.get_filter_for_unapproved(self.request.user.contact)
        return queryset.filter(qs_unapproved)

    @staticmethod
    def get_filter_for_approved(contact):
        """
        Prepare filter params for approved timesheets
        :param contact: request.user.contact
        :return: Q object
        """
        qs_approved = Q(going_to_work_confirmation=True)
        if contact.company_contact.exists():
            qs_approved &= Q(supervisor_approved_at__isnull=False, supervisor__contact=contact)
        else:
            qs_approved &= Q(candidate_submitted_at__isnull=False, job_offer__candidate_contact__contact=contact)
        return qs_approved

    @staticmethod
    def get_filter_for_unapproved(contact):
        """
        Prepare filter params for unapproved timesheets
        :param contact: request.user.contact
        :return: Q object
        """
        now = timezone.now()
        ended_at = now - datetime.timedelta(hours=4)
        signed_delta = now - datetime.timedelta(hours=1)

        qs_unapproved = (
            Q(candidate_submitted_at__isnull=False) |
            Q(shift_ended_at__lt=ended_at)
        ) & (
            Q(supervisor_approved_at__isnull=True) |
            Q(supervisor_approved_at__gte=signed_delta)
        ) & Q(supervisor__contact=contact, going_to_work_confirmation=True)

        return qs_unapproved


class JobFilter(ActiveStateFilterMixin, FilterSet):

    active_states = NumberFilter(method='filter_active_state')
    shift_dates__shift_date = DateRangeFilter(distinct=True)

    class Meta:
        model = hr_models.Job
        fields = [
            'active_states', 'customer_representative', 'customer_company', 'jobsite', 'position', 'work_start_date',
            'provider_representative',
        ]


class ShiftFilter(FilterSet):
    job = UUIDFilter(method='filter_job')
    date__shift_date = DateRangeFilter(distinct=True)
    candidate = UUIDFilter(method='filter_candidate')
    client = UUIDFilter(method='filter_client')
    client_contact = UUIDFilter(method='filter_client_contact')

    class Meta:
        model = hr_models.Shift
        fields = ['job', 'date']

    def filter_job(self, queryset, name, value):
        return queryset.filter(date__job_id=value)

    def filter_candidate(self, queryset, name, value):
        return queryset.filter(
            job_offers__candidate_contact_id=value
        ).distinct()

    def filter_client(self, queryset, name, value):
        return queryset.filter(
            date__job__customer_company_id=value
        ).distinct()

    def filter_client_contact(self, queryset, name, value):
        return queryset.filter(
            date__job__customer_representative_id=value
        ).distinct()


class JobOfferFilter(FilterSet):
    job = UUIDFilter(method='filter_job')
    shift_date = UUIDFilter(method='filter_shift_date')

    class Meta:
        model = hr_models.JobOffer
        fields = ['job', 'shift_date', 'candidate_contact']

    def filter_job(self, queryset, name, value):
        return queryset.filter(shift__date__job_id=value)

    def filter_shift_date(self, queryset, name, value):
        return queryset.filter(shift__date_id=value)


class JobsiteFilter(ActiveStateFilterMixin, FilterSet):
    company = UUIDFilter(method='filter_company')
    state = UUIDFilter(method='filter_state')
    active_states = NumberFilter(method='filter_active_state')

    class Meta:
        model = hr_models.Jobsite
        fields = [
            'company', 'active_states', 'primary_contact', 'short_name', 'industry', 'regular_company',
            'portfolio_manager'
        ]

    def filter_company(self, queryset, name, value):
        return queryset.filter(regular_company_id=value)

    def filter_state(self, queryset, name, value):
        return queryset.filter(address__state=value)


class FavouriteListFilter(FilterSet):

    class Meta:
        model = hr_models.FavouriteList
        fields = ['company_contact', 'candidate_contact', 'company', 'jobsite', 'job']


class CarrierListFilter(FilterSet):

    target_date = DateRangeFilter(distinct=True)

    class Meta:
        model = hr_models.CarrierList
        fields = ['candidate_contact', 'target_date']


class BlackListFilter(FilterSet):

    class Meta:
        model = hr_models.BlackList
        fields = ['candidate_contact']


class CandidateEvaluationFilter(FilterSet):

    class Meta:
        model = hr_models.CandidateEvaluation
        fields = ['candidate_contact']


class JobTagFilter(FilterSet):

    class Meta:
        model = hr_models.JobTag
        fields = ['job', 'tag__confidential']


class InvoiceFilter(FilterSet):

    class Meta:
        model = Invoice
        fields = ['customer_company']
