from django_filters.rest_framework import FilterSet

from r3sourcer.apps.acceptance_tests.models import AcceptanceTestWorkflowNode


class AcceptanceTestWorkflowNodeFilter(FilterSet):

    class Meta:
        model = AcceptanceTestWorkflowNode
        fields = ['company_workflow_node']
