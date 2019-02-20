from django.db.models import Q
from django.utils import timezone
from django_filters import UUIDFilter
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


class IndustryFilter(FilterSet):

    company = UUIDFilter(method='filter_by_company_price_lists')

    class Meta:
        model = models.Industry
        fields = ['company']

    def filter_by_company_price_lists(self, queryset, name, value):
        now = timezone.now()

        return queryset.filter(
            Q(skillname__skills__company_id=value) |
            Q(skillname__skills__price_list_rates__price_list__company_id=value,
              skillname__skills__price_list_rates__price_list__effective=True,
              skillname__skills__price_list_rates__price_list__valid_from__lte=now,
              skillname__skills__price_list_rates__price_list__valid_until__gte=now)
        ).distinct()


class RateCoefficientFilter(FilterSet):

    class Meta:
        model = models.RateCoefficient
        fields = ['industry']
