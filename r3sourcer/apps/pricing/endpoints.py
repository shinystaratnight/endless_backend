from drf_auto_endpoint.router import router

from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from .api import serializers
from . import models


class DynamicCoefficientRuleEndpoint(ApiEndpoint):

    model = models.DynamicCoefficientRule
    serializer = serializers.DynamicCoefficientRuleSerializer


class RateCoefficientEndpoint(ApiEndpoint):

    model = models.RateCoefficient
    serializer = serializers.RateCoefficientSerializer


router.register(endpoint=RateCoefficientEndpoint())
router.register(models.RateCoefficientGroup)
router.register(models.RateCoefficientModifier)
router.register(models.Industry)
router.register(models.IndustryPriceList)
router.register(models.IndustryPriceListRate)
router.register(models.IndustryRateCoefficient)
router.register(models.PriceList)
router.register(models.PriceListRate)
router.register(models.PriceListRateCoefficient)
router.register(endpoint=DynamicCoefficientRuleEndpoint())

router.register(models.WeekdayWorkRule)
router.register(models.OvertimeWorkRule)
router.register(models.TimeOfDayWorkRule)
router.register(models.AllowanceWorkRule)