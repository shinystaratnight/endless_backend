from django.db.models import Avg

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
                'acceptance_tests_workflow_nodes': ('id', 'company_workflow_node'),
            }
        )


class AcceptanceTestWorkflowNodeSerializer(ApiBaseModelSerializer):

    method_fields = ('score', )

    class Meta:
        model = models.AcceptanceTestWorkflowNode
        fields = ('id', 'acceptance_test', 'company_workflow_node')

    def __init__(self, *args, **kwargs):
        self.workflow_object_id = kwargs.pop('workflow_object_id', None)

        super().__init__(*args, **kwargs)

    def get_score(self, obj):
        return obj.get_score(self.workflow_object_id)


class AcceptanceTestCandidateWorkflowSerializer(ApiBaseModelSerializer):

    method_fields = ('score', )

    class Meta:
        model = models.AcceptanceTestWorkflowNode
        fields = ('id', 'acceptance_test', 'company_workflow_node')

    def __init__(self, *args, **kwargs):
        self.object_id = kwargs.pop('object_id', None)

        super().__init__(*args, **kwargs)

    def get_score(self, obj):
        return obj.get_all_questions().filter(
            workflow_object_answers__workflow_object__object_id=self.object_id
        ).aggregate(score_avg=Avg('workflow_object_answers__score'))['score_avg'] or 0


class WorkflowObjectAnswerSerializer(ApiBaseModelSerializer):

    class Meta:
        model = models.WorkflowObjectAnswer
        fields = ('id', 'acceptance_test_question', 'workflow_object', 'answer', 'answer_text', 'score', 'exclude')
