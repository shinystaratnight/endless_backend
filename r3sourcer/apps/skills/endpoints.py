from drf_auto_endpoint.router import router

from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.core_adapter import constants
from r3sourcer.apps.skills import models


class SkillEndpoint(ApiEndpoint):

    model = models.Skill
    fieldsets = (
        'name', 'short_name',  'carrier_list_reserve', 'employment_classification', 'active',
        {
            'field': 'skill_rate_defaults',
            'type': constants.FIELD_RELATED,
            'list': True
        },
        {
            'field': 'price_list_rates',
            'type': constants.FIELD_RELATED,
            'list': True
        }
    )

    list_display = (
        {
            'field': 'name',
            'type': constants.FIELD_TEXT
        },
        {
            'field': 'active',
            'type': constants.FIELD_TEXT
        },
        {
            'field': 'carrier_list_reserve',
            'type': constants.FIELD_TEXT
        }
    )

    search_fields = (
        'name',
    )

    def get_list_filter(self):
        return [{
            'type': constants.FIELD_SELECT,
            'field': 'active',
            'choices': [{'label': 'True', 'value': 'True'},
                        {'label': 'False', 'value': 'False'}],
        }]


class EmploymentClassificationEndpoint(ApiEndpoint):
    model = models.EmploymentClassification
    search_fields = ('name',)


class SkillBaseRateEndpoint(ApiEndpoint):
    model = models.SkillBaseRate
    search_fields = ('skill__name',)
    list_display = (
        {
            "field": "hourly_rate",
            "type": constants.FIELD_TEXT
        },
        {
            "field": "default_rate",
            "type": constants.FIELD_CHECKBOX
        }
    )


router.register(endpoint=SkillEndpoint())
router.register(endpoint=SkillBaseRateEndpoint())
router.register(endpoint=EmploymentClassificationEndpoint())
