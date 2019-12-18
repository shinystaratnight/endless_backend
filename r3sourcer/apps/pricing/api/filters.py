from django.db.models import Q
from django_filters import UUIDFilter
from django_filters.rest_framework import FilterSet

from r3sourcer.apps.pricing import models
from r3sourcer.helpers.datetimes import utc_now


class PriceListRateFilter(FilterSet):

    class Meta:
        model = models.PriceListRate
        fields = ['skill', 'price_list']


class RateCoefficientModifierFilter(FilterSet):

    class Meta:
        model = models.RateCoefficientModifier
        fields = ['rate_coefficient', 'type', 'default']


class PriceListFilter(FilterSet):

    class Meta:
        model = models.PriceList
        fields = ['company']


class IndustryFilter(FilterSet):

    company = UUIDFilter(method='filter_by_company_price_lists')

    class Meta:
        model = models.Industry
        fields = ['company']

    def filter_by_company_price_lists(self, queryset, name, value):
        return queryset.filter(
            Q(skillname__skills__company_id=value) |
            Q(skillname__skills__price_list_rates__price_list__company_id=value,
              skillname__skills__price_list_rates__price_list__effective=True,
              skillname__skills__price_list_rates__price_list__valid_from__lte=utc_now(),
              skillname__skills__price_list_rates__price_list__valid_until__gte=utc_now())
        ).distinct()


class RateCoefficientFilter(FilterSet):

    class Meta:
        model = models.RateCoefficient
        fields = ['industry']
