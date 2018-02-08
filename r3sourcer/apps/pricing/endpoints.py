from django.utils.translation import ugettext_lazy as _
from drf_auto_endpoint.router import router

from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.core_adapter import constants
from r3sourcer.apps.core.utils.text import format_lazy
from r3sourcer.apps.core_adapter.utils import api_reverse_lazy
from r3sourcer.apps.pricing import models
from r3sourcer.apps.pricing.api import serializers, viewsets


class DynamicCoefficientRuleEndpoint(ApiEndpoint):
    model = models.DynamicCoefficientRule
    serializer = serializers.DynamicCoefficientRuleSerializer


class RateCoefficientEndpoint(ApiEndpoint):
    model = models.RateCoefficient
    base_viewset = viewsets.RateCoefficientViewset
    serializer = serializers.RateCoefficientSerializer

    list_display = ('__str__', 'industry', 'rules', 'group', 'active')

    fieldsets = (
        {
            'type': constants.CONTAINER_ROW,
            'label': '{name}',
            'fields': (
                {
                    'type': constants.CONTAINER_COLUMN,
                    'fields': ('industry', 'name', {
                        'type': constants.FIELD_RELATED,
                        'field': 'group',
                    }, 'active'),
                },
            )
        }, {
            'type': constants.CONTAINER_ROW,
            'label': _('Overtime'),
            'fields': (
                {
                    'type': constants.CONTAINER_COLUMN,
                    'fields': ('overtime.used', 'overtime.overtime_hours_from', 'overtime.overtime_hours_to', {
                        'field': 'overtime.id',
                        'type': constants.FIELD_TEXT,
                        'hidden': True,
                    }),
                },
            )
        }, {
            'type': constants.CONTAINER_ROW,
            'label': _('Weekdays'),
            'fields': (
                {
                    'type': constants.CONTAINER_COLUMN,
                    'fields': (
                        'weekdays.weekday_monday', 'weekdays.weekday_tuesday', 'weekdays.weekday_wednesday',
                        'weekdays.weekday_thursday', 'weekdays.weekday_friday', 'weekdays.weekday_saturday',
                        'weekdays.weekday_sunday', 'weekdays.weekday_bank_holiday', {
                            'field': 'weekdays.id',
                            'type': constants.FIELD_TEXT,
                            'hidden': True,
                        }
                    ),
                },
            )
        }, {
            'type': constants.CONTAINER_ROW,
            'label': _('Time'),
            'fields': (
                {
                    'type': constants.CONTAINER_COLUMN,
                    'fields': ('timeofday.used', 'timeofday.time_start', 'timeofday.time_end', {
                        'field': 'timeofday.id',
                        'type': constants.FIELD_TEXT,
                        'hidden': True,
                    }),
                },
            )
        }, {
            'type': constants.CONTAINER_ROW,
            'label': _('Manual'),
            'fields': (
                {
                    'type': constants.CONTAINER_COLUMN,
                    'fields': ('allowance.used', {
                        'type': constants.FIELD_TEXTAREA,
                        'field': 'allowance.allowance_description'
                    }, {
                        'field': 'allowance.id',
                        'type': constants.FIELD_TEXT,
                        'hidden': True,
                    }),
                },
            )
        },
        {
            'type': constants.FIELD_LIST,
            'query': {
                'rate_coefficient': '{id}',
                'type': '1',
            },
            'add_label': _('Add'),
            'max': 1,
            'label': _('Rate Coefficients for Candidates'),
            'endpoint': api_reverse_lazy('pricing/ratecoefficientmodifiers'),
            'prefilled': {
                'rate_coefficient': '{id}',
                'type': '1',
            }
        },
        {
            'type': constants.FIELD_LIST,
            'query': {
                'rate_coefficient': '{id}',
                'type': '0',
            },
            'add_label': _('Add'),
            'max': 1,
            'label': _('Rate Coefficients for Companies'),
            'endpoint': api_reverse_lazy('pricing/ratecoefficientmodifiers'),
            'prefilled': {
                'rate_coefficient': '{id}',
                'type': '0',
            }
        },
    )

    list_filter = ('industry', )


class PriceListRateEndpoint(ApiEndpoint):
    model = models.PriceListRate
    search_fields = ('skill__name',)
    fieldsets = (
        {
            "field": "hourly_rate",
            "type": constants.FIELD_TEXT
        },
        {
            "field": "default_rate",
            "type": constants.FIELD_CHECKBOX
        }
    )


class RateCoefficientModifierEndpoint(ApiEndpoint):
    model = models.RateCoefficientModifier
    list_filter = ('rate_coefficient', 'type')

    list_editable = ('multiplier', 'fixed_addition', 'fixed_override', {
        'label': _('Actions'),
        'delim': ' ',
        'fields': ({
            **constants.BUTTON_EDIT,
            'endpoint': format_lazy('{}{{id}}', api_reverse_lazy('pricing/ratecoefficientmodifiers'))
        }, constants.BUTTON_DELETE, )
    },)


class PriceListEndpoint(ApiEndpoint):
    model = models.PriceList

    list_filter = ('company', )
    list_editable = ('valid_from', 'valid_until', 'effective', 'approved_by', 'approved_at', {
        **constants.BUTTON_EDIT,
        'endpoint': format_lazy('{}{{id}}', api_reverse_lazy('pricing/pricelists'))
    }, constants.BUTTON_DELETE,)


class IndustryEndpoint(ApiEndpoint):
    model = models.Industry
    serializer = serializers.IndustrySerializer

    list_display = ('type', )
    fieldsets = ('type', )


router.register(endpoint=RateCoefficientEndpoint())
router.register(models.RateCoefficientGroup)
router.register(endpoint=RateCoefficientModifierEndpoint())
router.register(endpoint=IndustryEndpoint())
router.register(endpoint=PriceListEndpoint())
router.register(endpoint=PriceListRateEndpoint())
router.register(models.PriceListRateCoefficient)
router.register(endpoint=DynamicCoefficientRuleEndpoint())

router.register(models.WeekdayWorkRule)
router.register(models.OvertimeWorkRule)
router.register(models.TimeOfDayWorkRule)
router.register(models.AllowanceWorkRule)
