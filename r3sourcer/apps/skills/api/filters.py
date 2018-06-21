from django.utils import timezone
from django_filters import UUIDFilter
from django_filters.rest_framework import FilterSet

from r3sourcer.apps.skills import models as skills_models


class SkillFilter(FilterSet):
    company = UUIDFilter(method='filter_by_company_price_lists')
    exclude = UUIDFilter(method='exclude_by_candidate')

    class Meta:
        model = skills_models.Skill
        fields = ['company', 'active']

    def filter_by_company_price_lists(self, queryset, name, value):
        now = timezone.now()
        return queryset.filter(
            price_list_rates__price_list__company_id=value,
            price_list_rates__price_list__effective=True,
            price_list_rates__price_list__valid_from__lte=now,
            price_list_rates__price_list__valid_until__gte=now,
        )

    def exclude_by_candidate(self, queryset, name, value):
        return queryset.filter(active=True).exclude(
            candidate_skills__candidate_contact_id=value
        )


class SkillBaseRateFilter(FilterSet):
    candidate_skill = UUIDFilter(method='filter_candidate_skill')

    class Meta:
        model = skills_models.SkillBaseRate
        fields = ['candidate_skill']

    def filter_candidate_skill(self, queryset, name, value):
        return queryset.filter(skill__candidate_skills=value).distinct()
