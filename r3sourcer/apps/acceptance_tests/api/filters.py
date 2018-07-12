from django_filters import UUIDFilter
from django_filters.rest_framework import FilterSet

from r3sourcer.apps.acceptance_tests import models


class AcceptanceTestFilter(FilterSet):

    skill = UUIDFilter(method='filter_skill')
    tag = UUIDFilter(method='filter_tag')
    industry = UUIDFilter(method='filter_industry')

    class Meta:
        model = models.AcceptanceTest
        fields = ['skill', 'tag', 'industry']

    def get_filter_skill(self, queryset, name, value):
        return queryset.filter(acceptance_tests_skills__skill=value)

    def get_filter_tag(self, queryset, name, value):
        return queryset.filter(acceptance_tests_tags__tag=value)

    def get_filter_industry(self, queryset, name, value):
        return queryset.filter(acceptance_tests_industries__industry=value)


class AcceptanceTestWorkflowNodeFilter(FilterSet):

    class Meta:
        model = models.AcceptanceTestWorkflowNode
        fields = ['company_workflow_node']
