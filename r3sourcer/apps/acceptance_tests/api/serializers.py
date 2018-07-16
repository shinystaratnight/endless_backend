from r3sourcer.apps.acceptance_tests.models import AcceptanceTestWorkflowNode, AcceptanceTest
from r3sourcer.apps.core.api.fields import ApiBaseRelatedField
from r3sourcer.apps.core.api.serializers import ApiBaseModelSerializer


class AcceptanceTestSerializer(ApiBaseModelSerializer):

    method_fields = ('tags', 'skills', 'industries')

    class Meta:
        model = AcceptanceTest
        fields = (
            'test_name', 'description', 'valid_from', 'valid_until', 'is_active', 'id',
            {
                'acceptance_test_questions': (
                    'id', 'question', 'details', 'order', 'type',
                    {
                        'acceptance_test_answers': ('id',  'answer', 'order', 'score', ),
                    },
                ),
            }
        )

    def get_skills(self, obj):
        return [ApiBaseRelatedField.to_read_only_data(skill) for skill in obj.skills.all()]

    def get_tags(self, obj):
        return [ApiBaseRelatedField.to_read_only_data(tag) for tag in obj.tags.all()]

    def get_industries(self, obj):
        return [ApiBaseRelatedField.to_read_only_data(industry) for industry in obj.industries.all()]


class AcceptanceTestWorkflowNodeSerializer(ApiBaseModelSerializer):

    class Meta:
        model = AcceptanceTestWorkflowNode
        fields = ('id', 'acceptance_test', 'company_workflow_node', 'score')
