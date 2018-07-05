from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _
from django_filters import ModelMultipleChoiceFilter, NumberFilter, MultipleChoiceFilter
from django_filters.rest_framework import FilterSet

from r3sourcer.apps.candidate.models import CandidateContact, SkillRel, TagRel
from r3sourcer.apps.core.api.mixins import ActiveStateFilterMixin
from r3sourcer.apps.core.models import Tag, WorkflowObject
from r3sourcer.apps.skills.models import Skill


class CandidateContactFilter(ActiveStateFilterMixin, FilterSet):

    skill = ModelMultipleChoiceFilter(queryset=Skill.objects.all(), method='filter_skill')
    tag = ModelMultipleChoiceFilter(queryset=Tag.objects.all(), method='filter_tag')
    active_states = NumberFilter(method='filter_active_state')
    contact__gender = MultipleChoiceFilter(choices=(("male", _("Male")), ("female", _("Female"))))
    transportation_to_work = MultipleChoiceFilter(choices=CandidateContact.TRANSPORTATION_CHOICES)

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

    def _fetch_workflow_objects(self, value):  # pragma: no cover
        content_type = ContentType.objects.get_for_model(self.Meta.model)
        exclude_values = WorkflowObject.objects.filter(
            state__number__gt=value, state__workflow__model=content_type, active=True
        ).values_list('object_id', flat=True)

        return WorkflowObject.objects.filter(
            state__number=value, state__workflow__model=content_type, active=True,
        ).exclude(
            object_id__in=set(exclude_values)
        ).distinct('object_id').values_list('object_id', flat=True)


class SkillRelFilter(FilterSet):

    class Meta:
        model = SkillRel
        fields = ['candidate_contact']


class TagRelFilter(FilterSet):

    class Meta:
        model = TagRel
        fields = ['candidate_contact']
