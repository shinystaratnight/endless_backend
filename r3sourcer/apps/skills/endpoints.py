from r3sourcer.apps.core.api.router import router

from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.skills import models
from r3sourcer.apps.skills.api import filters as skills_filters, serializers as skill_serializer


class SkillEndpoint(ApiEndpoint):

    model = models.Skill
    filter_class = skills_filters.SkillFilter
    serializer = skill_serializer.SkillSerializer

    search_fields = ('name', )


class EmploymentClassificationEndpoint(ApiEndpoint):

    model = models.EmploymentClassification
    search_fields = ('name', )
    serializer_fields = ('name', )


class SkillBaseRateEndpoint(ApiEndpoint):
    model = models.SkillBaseRate
    serializer = skill_serializer.SkillBaseRateSerializer
    filter_class = skills_filters.SkillBaseRateFilter
    search_fields = ('skill__name', )


router.register(endpoint=SkillEndpoint())
router.register(endpoint=SkillBaseRateEndpoint())
router.register(endpoint=EmploymentClassificationEndpoint())
