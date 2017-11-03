from django_filters import UUIDFilter
from django_filters.rest_framework import FilterSet

from ..models import TimeSheet


class TimesheetFilter(FilterSet):
    candidate = UUIDFilter(method='filter_candidate')

    class Meta:
        model = TimeSheet
        fields = ['supervisor']

    def filter_candidate(self, queryset, name, value):
        return queryset.filter(
            vacancy_offer__candidate_contact_id=value
        )
