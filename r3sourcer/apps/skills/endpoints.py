from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from drf_auto_endpoint.router import router

from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.core.utils.text import format_lazy
from r3sourcer.apps.core_adapter import constants
from r3sourcer.apps.core_adapter.utils import api_reverse_lazy
from r3sourcer.apps.skills import models
from r3sourcer.apps.skills.api import filters as skills_filters, serializers as skill_serializer


class SkillEndpoint(ApiEndpoint):
    model = models.Skill
    filter_class = skills_filters.SkillFilter
    serializer = skill_serializer.SkillSerializer

    fieldsets = (
        'name', 'short_name',  'carrier_list_reserve', 'employment_classification', 'active',
        {
            'type': constants.FIELD_LIST,
            'field': 'id_',
            'query': {
                'skill': '{id}',
            },
            'collapsed': False,
            'label': _('Skill Rate Defaults'),
            'add_label': _('Add'),
            'endpoint': api_reverse_lazy('skills/skillbaserates'),
            'prefilled': {
                'skill': '{id}',
            }
        }, {
            'type': constants.FIELD_LIST,
            'field': 'id_',
            'query': {
                'skill': '{id}',
            },
            'collapsed': False,
            'label': _('Price List Rates'),
            'add_label': _('Add'),
            'endpoint': api_reverse_lazy('pricing/pricelistrates'),
            'prefilled': {
                'skill': '{id}',
            }
        },
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
    serializer = skill_serializer.SkillBaseRateSerializer

    search_fields = ('skill__name',)
    filter_fields = ('skill', )
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

    list_editable = (
        'hourly_rate', 'default_rate',
        {
            'label': _('Actions'),
            'delim': ' ',
            'fields': ({
                **constants.BUTTON_EDIT,
                'endpoint': format_lazy('{}{{id}}', api_reverse_lazy('skills/skillbaserates'))
            }, constants.BUTTON_DELETE)
        },
    )
    list_editable_buttons = []


router.register(endpoint=SkillEndpoint())
router.register(endpoint=SkillBaseRateEndpoint())
router.register(endpoint=EmploymentClassificationEndpoint())
