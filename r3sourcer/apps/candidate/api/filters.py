from django_filters import ModelMultipleChoiceFilter
from django_filters.rest_framework import FilterSet

from r3sourcer.apps.candidate.models import CandidateContact
from r3sourcer.apps.core.models import Tag
from r3sourcer.apps.skills.models import Skill


class CandidateContactFilter(FilterSet):

    skill = ModelMultipleChoiceFilter(queryset=Skill.objects.all(), method='filter_skill')
    tag = ModelMultipleChoiceFilter(queryset=Tag.objects.all(), method='filter_tag')

    class Meta:
        model = CandidateContact
        fields = ['skill', 'tag']

    def filter_skill(self, queryset, name, value):
        if not value:
            return queryset

        return queryset.filter(candidate_skills__skill__in=value)

    def filter_tag(self, queryset, name, value):
        if not value:
            return queryset

        return queryset.filter(tag_rels__tag__in=value)
