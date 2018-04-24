from django_filters import ModelMultipleChoiceFilter, NumberFilter, CharFilter
from django_filters.rest_framework import FilterSet

from r3sourcer.apps.candidate.models import CandidateContact
from r3sourcer.apps.core.api.mixins import ActiveStateFilterMixin
from r3sourcer.apps.core.models import Tag
from r3sourcer.apps.skills.models import Skill


class CandidateContactFilter(ActiveStateFilterMixin, FilterSet):

    skill = ModelMultipleChoiceFilter(queryset=Skill.objects.all(), method='filter_skill')
    tag = ModelMultipleChoiceFilter(queryset=Tag.objects.all(), method='filter_tag')
    active_states = NumberFilter(method='filter_active_state')
    contact__gender = CharFilter()

    class Meta:
        model = CandidateContact
        fields = ['skill', 'tag', 'transportation_to_work']

    def filter_skill(self, queryset, name, value):
        if not value:
            return queryset

        return queryset.filter(candidate_skills__skill__in=value)

    def filter_tag(self, queryset, name, value):
        if not value:
            return queryset

        return queryset.filter(tag_rels__tag__in=value)
