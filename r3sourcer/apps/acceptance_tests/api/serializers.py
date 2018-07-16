from r3sourcer.apps.acceptance_tests.models import AcceptanceTestWorkflowNode
from r3sourcer.apps.core.api.serializers import ApiBaseModelSerializer


class AcceptanceTestWorkflowNodeSerializer(ApiBaseModelSerializer):

    class Meta:
        model = AcceptanceTestWorkflowNode
        fields = ('id', 'acceptance_test', 'company_workflow_node', 'score')
