import datetime

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils import timezone

from django_filters import UUIDFilter, NumberFilter, BooleanFilter, DateFromToRangeFilter, DateFilter
from django_filters.rest_framework import FilterSet

from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.hr import models as hr_models


class TimesheetFilter(FilterSet):
    candidate = UUIDFilter(method='filter_candidate')
    approved = BooleanFilter(method='filter_approved')
    company = UUIDFilter('job_offer__shift__date__job__customer_company_id')
    jobsite = UUIDFilter('job_offer__shift__date__job__jobsite_id')

    class Meta:
        model = hr_models.TimeSheet
        fields = ['shift_started_at']

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


class JobFilter(FilterSet):
    active_states = NumberFilter(method='filter_state')

    class Meta:
        model = hr_models.Job
        fields = ['active_states']

    def _fetch_workflow_objects(self, value):  # pragma: no cover
        content_type = ContentType.objects.get_for_model(hr_models.Job)
        objects = core_models.WorkflowObject.objects.filter(
            state__number=value,
            state__workflow__model=content_type,
            active=True,
        ).distinct('object_id').values_list('object_id', flat=True)

        return objects

    def filter_state(self, queryset, name, value):
        objects = self._fetch_workflow_objects(value)
        return queryset.filter(id__in=objects)


class ShiftFilter(FilterSet):
    job = UUIDFilter(method='filter_job')
    date__shift_date = DateFilter()

    class Meta:
        model = hr_models.Shift
        fields = ['job', 'date']

    def filter_job(self, queryset, name, value):
        return queryset.filter(date__job_id=value)


class JobOfferFilter(FilterSet):
    job = UUIDFilter(method='filter_job')

    class Meta:
        model = hr_models.Shift
        fields = ['job']

    def filter_job(self, queryset, name, value):
        return queryset.filter(shift__date__job_id=value)


class JobsiteFilter(FilterSet):
    company = UUIDFilter(method='filter_company')

    class Meta:
        model = hr_models.Jobsite
        fields = ['company']

    def filter_company(self, queryset, name, value):
        return queryset.filter(
            Q(master_company_id=value) |
            Q(jobsite_addresses__regular_company_id=value)
        )


class JobsiteAddressFilter(FilterSet):
    company = UUIDFilter(method='filter_company')

    class Meta:
        model = hr_models.JobsiteAddress
        fields = ['company']

    def filter_company(self, queryset, name, value):
        return queryset.filter(
            Q(jobsite__master_company_id=value) |
            Q(regular_company_id=value)
        )
