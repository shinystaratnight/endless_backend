from r3sourcer.apps.acceptance_tests.api import filters
from r3sourcer.apps.core.api.router import router
from r3sourcer.apps.core.api.endpoints import ApiEndpoint

from . import models


class AcceptanceTestWorkflowNodeEndpoint(ApiEndpoint):

    model = models.AcceptanceTestWorkflowNode
    filter_calss = filters.AcceptanceTestWorkflowNodeFilter
    serializer_fields = ('id', 'acceptance_test', 'company_workflow_node')


router.register(models.AcceptanceTest)
router.register(models.AcceptanceTestQuestion)
router.register(models.AcceptanceTestAnswer)
router.register(models.AcceptanceTestSkill)
router.register(models.AcceptanceTestIndustry)
router.register(models.AcceptanceTestTag)
router.register(models.AcceptanceTestWorkflowNode)
