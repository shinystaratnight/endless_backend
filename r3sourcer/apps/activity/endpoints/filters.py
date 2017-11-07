from django_filters.rest_framework import FilterSet

from ..models import Activity


class ActivityFilter(FilterSet):

    class Meta:
        model = Activity
        fields = ('done', 'priority', 'contact', 'starts_at', 'ends_at')
