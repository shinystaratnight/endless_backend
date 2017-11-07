from drf_auto_endpoint.router import router

from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from . import models


class SkillEndpoint(ApiEndpoint):

    model = models.Skill

    fieldsets = ('name', 'short_name',  'carrier_list_reserve',
                 'employment_classification', 'active')


router.register(endpoint=SkillEndpoint())
router.register(models.SkillBaseRate)
router.register(models.EmploymentClassification)
