import datetime

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils import timezone

from django_filters import UUIDFilter, NumberFilter, BooleanFilter
from django_filters.rest_framework import FilterSet

from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.hr import models as hr_models


class TimesheetFilter(FilterSet):
    candidate = UUIDFilter(method='filter_candidate')
    approved = BooleanFilter(method='filter_approved')

    class Meta:
        model = hr_models.TimeSheet
        fields = ['supervisor']

    def filter_candidate(self, queryset, name, value):
        return queryset.filter(
            vacancy_offer__candidate_contact_id=value
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
            qs_approved &= Q(supervisor_approved_at__isnull=False)
        else:
            qs_approved &= Q(candidate_submitted_at__isnull=False)
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

        qs_unapproved = (Q(candidate_submitted_at__isnull=False) |
                        Q(shift_ended_at__lt=ended_at)) &\
                        (Q(supervisor_approved_at__isnull=True) |
                        Q(supervisor_approved_at__gte=signed_delta)) &\
                        Q(supervisor__contact=contact) &\
                        Q(going_to_work_confirmation=True)
        return qs_unapproved


class VacancyFilter(FilterSet):
    active_states = NumberFilter(method='filter_state')

    class Meta:
        model = hr_models.Vacancy
        fields = ['active_states']

    def _fetch_workflow_objects(self, value):  # pragma: no cover
        content_type = ContentType.objects.get_for_model(hr_models.Vacancy)
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
    vacancy = UUIDFilter(method='filter_vacancy')

    class Meta:
        model = hr_models.Shift
        fields = ['vacancy']

    def filter_vacancy(self, queryset, name, value):
        return queryset.filter(date__vacancy_id=value)


class VacancyOfferFilter(FilterSet):
    vacancy = UUIDFilter(method='filter_vacancy')

    class Meta:
        model = hr_models.Shift
        fields = ['vacancy']

    def filter_vacancy(self, queryset, name, value):
        return queryset.filter(shift__date__vacancy_id=value)
