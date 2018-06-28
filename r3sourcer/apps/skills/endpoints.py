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
        {
            'field': 'id',
            'type': constants.FIELD_INFO,
            'values': {
                'carrier_reserve': 'carrier_list_reserve',
                'available': 'active',
                'title': 'name',
                'created_at': 'created_at',
                'updated_at': 'updated_at',
            }
        }, {
            'type': constants.CONTAINER_TABS,
            'fields': ({
                'type': constants.CONTAINER_GROUP,
                'label': _('Skill information'),
                'name': _('Skill Info'),
                'main': True,
                'fields': ({
                    'type': constants.CONTAINER_ROW,
                    'fields': (
                        {
                            'type': constants.CONTAINER_GROUP,
                            'label': _('Additional Info'),
                            'width': .34,
                            'fields': (
                                'short_name',
                                {
                                    'type': constants.FIELD_RELATED,
                                    'field': 'employment_classification',
                                    'read_only': False,
                                },
                            ),
                        }, {
                            'type': constants.CONTAINER_GROUP,
                            'label': _('Skill Rate'),
                            'width': .33,
                            'fields': (
                                {
                                    'type': constants.FIELD_NUMBER,
                                    'field': 'lower_rate_limit',
                                    'label': _('Lower Rate Limit'),
                                    'display': '${field}/h',
                                }, {
                                    'type': constants.FIELD_NUMBER,
                                    'field': 'default_rate',
                                    'label': _('Default Rate'),
                                    'display': '${field}/h',
                                    'read_only': False,
                                }, {
                                    'type': constants.FIELD_NUMBER,
                                    'field': 'upper_rate_limit',
                                    'label': _('Upper Rate Limit'),
                                    'display': '${field}/h',
                                },
                            ),
                        }, {
                            'type': constants.CONTAINER_GROUP,
                            'label': _('Price List Rate'),
                            'width': .33,
                            'fields': (
                                {
                                    'type': constants.FIELD_NUMBER,
                                    'field': 'lower_rate_limit',
                                    'label': _('Lower Rate Limit'),
                                    'display': '${field}/h',
                                }, {
                                    'type': constants.FIELD_NUMBER,
                                    'field': 'default_rate',
                                    'label': _('Default Rate'),
                                    'display': '${field}/h',
                                    'read_only': False,
                                }, {
                                    'type': constants.FIELD_NUMBER,
                                    'field': 'upper_rate_limit',
                                    'label': _('Upper Rate Limit'),
                                    'display': '${field}/h',
                                },
                            ),
                        },
                    ),
                },)
            },)
        }, {
            'field': 'active',
            'type': constants.FIELD_CHECKBOX,
            'hide': True,
            'default': False,
        }, {
            'field': 'name',
            'type': constants.FIELD_TEXT,
            'hide': True,
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
    filter_class = skills_filters.SkillBaseRateFilter

    search_fields = ('skill__name',)
    filter_fields = ('skill', )
    list_display = (
        {
            "field": "hourly_rate",
            "type": constants.FIELD_TEXT
        },
    )

    list_editable = (
        'hourly_rate',
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
