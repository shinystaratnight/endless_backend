from django.db.models import Q
from django_filters import UUIDFilter
from django_filters.rest_framework import FilterSet

from r3sourcer.apps.pricing import models
from r3sourcer.helpers.datetimes import utc_now


class PriceListRateFilter(FilterSet):

    class Meta:
        model = models.PriceListRate
        fields = ['worktype', 'price_list']


class RateCoefficientModifierFilter(FilterSet):

    class Meta:
        model = models.RateCoefficientModifier
        fields = ['rate_coefficient', 'type', 'default']


class PriceListFilter(FilterSet):

    class Meta:
        model = models.PriceList
        fields = ['company']


class IndustryFilter(FilterSet):

    class Meta:
        model = models.Industry
        fields = ['company']


class RateCoefficientFilter(FilterSet):

    class Meta:
        model = models.RateCoefficient
        fields = ['industry']
