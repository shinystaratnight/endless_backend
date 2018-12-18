from r3sourcer.apps.core.api.router import router

from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.core.api.permissions import ReadonlyOrIsSuperUser
from r3sourcer.apps.skills import models
from r3sourcer.apps.skills.api import filters as skills_filters, serializers as skill_serializer


class SkillEndpoint(ApiEndpoint):

    model = models.Skill
    filter_class = skills_filters.SkillFilter
    serializer = skill_serializer.SkillSerializer
    permission_classes = (ReadonlyOrIsSuperUser, )

    search_fields = ('name__name', )


class EmploymentClassificationEndpoint(ApiEndpoint):

    model = models.EmploymentClassification
    search_fields = ('name', )
    serializer_fields = ('id', 'name', )


class SkillBaseRateEndpoint(ApiEndpoint):
    model = models.SkillBaseRate
    serializer = skill_serializer.SkillBaseRateSerializer
    filter_class = skills_filters.SkillBaseRateFilter
    search_fields = ('skill__name__name', )


class SkillTagEndpoint(ApiEndpoint):
    model = models.SkillTag
    filter_class = skills_filters.SkillTagFilter
    serializer = skill_serializer.SkillTagSerializer
    search_fields = ('skill__name__name', 'tag__name')


class SkillNameEndpoint(ApiEndpoint):

    model = models.SkillName
    filter_class = skills_filters.SkillNameFilter
    serializer = skill_serializer.SkillNameSerializer

    search_fields = ('name', )


router.register(endpoint=SkillNameEndpoint())
router.register(endpoint=SkillEndpoint())
router.register(endpoint=SkillBaseRateEndpoint())
router.register(endpoint=EmploymentClassificationEndpoint())
router.register(endpoint=SkillTagEndpoint())
