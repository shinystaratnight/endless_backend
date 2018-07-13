from r3sourcer.apps.acceptance_tests.api import filters
from r3sourcer.apps.core.api.router import router
from r3sourcer.apps.core.api.endpoints import ApiEndpoint

from . import models


class AcceptanceTestEndpoint(ApiEndpoint):

    model = models.AcceptanceTest
    filter_class = filters.AcceptanceTestFilter
    serializer_fields = (
        '__all__',
        {
            'acceptance_test_questions': (
                'id', 'question', 'details', 'order', 'type',
                {
                    'acceptance_test_answers': ('id',  'answer', 'order', 'score', ),
                },
            ),
        }
    )


class AcceptanceTestWorkflowNodeEndpoint(ApiEndpoint):

    model = models.AcceptanceTestWorkflowNode
    filter_class = filters.AcceptanceTestWorkflowNodeFilter
    serializer_fields = ('id', 'acceptance_test', 'company_workflow_node')


router.register(endpoint=AcceptanceTestEndpoint())
router.register(models.AcceptanceTestQuestion)
router.register(models.AcceptanceTestAnswer)
router.register(models.AcceptanceTestSkill)
router.register(models.AcceptanceTestIndustry)
router.register(models.AcceptanceTestTag)
router.register(endpoint=AcceptanceTestWorkflowNodeEndpoint())
router.register(models.WorkflowObjectAnswer)
