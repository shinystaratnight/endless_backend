from django.contrib.contenttypes.models import ContentType

from django_filters import UUIDFilter, NumberFilter
from django_filters.rest_framework import FilterSet

from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.hr import models as hr_models


class TimesheetFilter(FilterSet):
    candidate = UUIDFilter(method='filter_candidate')

    class Meta:
        model = hr_models.TimeSheet
        fields = ['supervisor']

    def filter_candidate(self, queryset, name, value):
        return queryset.filter(
            vacancy_offer__candidate_contact_id=value
        )


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
