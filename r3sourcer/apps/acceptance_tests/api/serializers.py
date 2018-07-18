from r3sourcer.apps.acceptance_tests import models
from r3sourcer.apps.core.api.serializers import ApiBaseModelSerializer


class AcceptanceTestSerializer(ApiBaseModelSerializer):

    class Meta:
        model = models.AcceptanceTest
        fields = (
            'test_name', 'description', 'valid_from', 'valid_until', 'is_active', 'id',
            {
                'acceptance_test_questions': (
                    'id', 'question', 'details', 'order', 'type',
                    {
                        'acceptance_test_answers': ('id',  'answer', 'order', 'score', ),
                    },
                ),
                'acceptance_tests_skills': ('id', 'skill'),
                'acceptance_tests_tags': ('id', 'tag'),
                'acceptance_tests_industries': ('id', 'industry'),
            }
        )


class AcceptanceTestWorkflowNodeSerializer(ApiBaseModelSerializer):

    class Meta:
        model = models.AcceptanceTestWorkflowNode
        fields = ('id', 'acceptance_test', 'company_workflow_node', 'score')


class WorkflowObjectAnswerSerializer(ApiBaseModelSerializer):

    class Meta:
        model = models.WorkflowObjectAnswer
        fields = ('id', 'acceptance_test_question', 'workflow_object', 'answer', 'answer_text', 'score', 'exclude')
