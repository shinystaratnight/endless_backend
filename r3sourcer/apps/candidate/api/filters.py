from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django_filters import ModelMultipleChoiceFilter, NumberFilter, MultipleChoiceFilter, BooleanFilter
from django_filters.rest_framework import FilterSet

from r3sourcer.apps.candidate.models import CandidateContact, SkillRel, TagRel, CandidateContactAnonymous
from r3sourcer.apps.core.api.mixins import ActiveStateFilterMixin
from r3sourcer.apps.core.models import Tag
from r3sourcer.apps.core_adapter.filters import DateRangeFilter, RangeNumberFilter
from r3sourcer.apps.skills.models import Skill


class CandidateContactFilter(ActiveStateFilterMixin, FilterSet):

    skill = ModelMultipleChoiceFilter(queryset=Skill.objects.all(), method='filter_skill')
    tag = ModelMultipleChoiceFilter(queryset=Tag.objects.all(), method='filter_tag')
    active_states = NumberFilter(method='filter_active_state')
    contact__gender = MultipleChoiceFilter(choices=(("male", _("Male")), ("female", _("Female"))))
    transportation_to_work = MultipleChoiceFilter(choices=CandidateContact.TRANSPORTATION_CHOICES)
    created_at = DateRangeFilter()
    candidate_scores__average_score = RangeNumberFilter()
    candidate_price = BooleanFilter(method='filter_candidate_price')

    class Meta:
        model = CandidateContact
        fields = ['skill', 'tag', 'contact', 'recruitment_agent']

    def filter_skill(self, queryset, name, value):
        if not value:
            return queryset

        for skill in value:
            queryset = queryset.filter(candidate_skills__skill=skill)

        return queryset

    def filter_tag(self, queryset, name, value):
        if not value:
            return queryset

        for tag in value:
            queryset = queryset.filter(tag_rels__tag=tag)

        return queryset

    def filter_candidate_price(self, queryset, name, value):
        if value:
            return queryset.exclude(profile_price=0.00)
        else:
            return queryset.filter(profile_price=0.00)


class CandidateContactAnonymousFilter(ActiveStateFilterMixin, FilterSet):

    skill = ModelMultipleChoiceFilter(queryset=Skill.objects.all(), method='filter_skill')
    tag = ModelMultipleChoiceFilter(queryset=Tag.objects.all(), method='filter_tag')
    contact__gender = MultipleChoiceFilter(choices=(("male", _("Male")), ("female", _("Female"))))
    transportation_to_work = MultipleChoiceFilter(choices=CandidateContact.TRANSPORTATION_CHOICES)
    created_at = DateRangeFilter()
    candidate_scores__average_score = RangeNumberFilter()

    class Meta:
        model = CandidateContactAnonymous
        fields = ['skill', 'tag', 'contact', 'recruitment_agent']

    def filter_skill(self, queryset, name, value):
        if not value:
            return queryset

        for skill in value:
            queryset = queryset.filter(Q(candidate_skills__skill__name=skill.name))

        return queryset

    def filter_tag(self, queryset, name, value):
        if not value:
            return queryset

        for tag in value:
            queryset = queryset.filter(tag_rels__tag=tag)

        return queryset


class SkillRelFilter(FilterSet):

    class Meta:
        model = SkillRel
        fields = ['candidate_contact']


class TagRelFilter(FilterSet):

    class Meta:
        model = TagRel
        fields = ['candidate_contact', 'tag__confidential']
