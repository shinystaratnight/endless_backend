from django.utils import timezone
from django_filters import UUIDFilter
from django_filters.rest_framework import FilterSet

from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.skills import models as skills_models


class SkillFilter(FilterSet):
    company = UUIDFilter(method='filter_by_company_price_lists')
    exclude = UUIDFilter(method='exclude_by_candidate')
    exclude_pricelist = UUIDFilter(method='exclude_by_pricelist')
    industry = UUIDFilter(method='filter_by_industry')

    class Meta:
        model = skills_models.Skill
        fields = ['company', 'active']

    def filter_by_company_price_lists(self, queryset, name, value):
        company = core_models.Company.objects.filter(id=value).first()

        if company and company.type == core_models.Company.COMPANY_TYPES.master:
            return queryset.filter(company=company).distinct()

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

    def exclude_by_pricelist(self, queryset, name, value):
        return queryset.exclude(
            price_list_rates__price_list_id=value
        )

    def filter_by_industry(self, queryset, name, value):
        return queryset.filter(name__industry=value).distinct()


class SkillBaseRateFilter(FilterSet):
    candidate_skill = UUIDFilter(method='filter_candidate_skill')

    class Meta:
        model = skills_models.SkillBaseRate
        fields = ['candidate_skill', 'skill']

    def filter_candidate_skill(self, queryset, name, value):
        return queryset.filter(skill__candidate_skills=value).distinct()


class SkillTagFilter(FilterSet):

    class Meta:
        model = skills_models.SkillTag
        fields = ['tag', 'skill', 'tag__confidential']


class SkillNameFilter(FilterSet):
    exclude_company = UUIDFilter(method='exclude_by_company')

    class Meta:
        model = skills_models.SkillName
        fields = ['industry']

    def exclude_by_company(self, queryset, name, value):
        return queryset.exclude(
            skills__company=value
        )
