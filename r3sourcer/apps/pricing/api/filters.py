from django_filters.rest_framework import FilterSet

from r3sourcer.apps.pricing import models


class PriceListRateFilter(FilterSet):

    class Meta:
        model = models.PriceListRate
        fields = ['skill', 'price_list']


class RateCoefficientModifierFilter(FilterSet):

    class Meta:
        model = models.RateCoefficientModifier
        fields = ['rate_coefficient', 'type']


class PriceListFilter(FilterSet):

    class Meta:
        model = models.PriceList
        fields = ['company']
