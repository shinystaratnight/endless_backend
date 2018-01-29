from django_filters import UUIDFilter
from django_filters.rest_framework import FilterSet

from r3sourcer.apps.skills import models as skills_models


class SkillFilter(FilterSet):
    company = UUIDFilter(method='filter_by_company_price_lists')

    class Meta:
        model = skills_models.Skill
        fields = ['company']

    def filter_by_company_price_lists(self, queryset, name, value):
        return queryset.filter(
            price_list_rates__price_list__company_id=value
        )
