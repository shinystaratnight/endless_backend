from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers, exceptions

from r3sourcer.apps.core.api.serializers import (
    ApiBaseModelSerializer, ContactRegisterSerializer, RELATED_DIRECT,
    ApiRealtedFieldManyMixin, ContactSerializer,
)
from r3sourcer.apps.core.models import Contact, Tag
from r3sourcer.apps.skills.models import Skill

from .. import models


class SkillRelSerializer(ApiBaseModelSerializer):

    class Meta:
        model = models.SkillRel
        fields = '__all__'


class TagRelSerializer(ApiBaseModelSerializer):

    class Meta:
        model = models.TagRel
        fields = '__all__'


class CandidateContactSerializer(ApiRealtedFieldManyMixin,
                                 ApiBaseModelSerializer):
    candidate_skills = SkillRelSerializer(many=True)
    tag_rels = TagRelSerializer(many=True)

    method_fields = ('state', 'total_score', 'bmi', 'skill_list', 'tag_list')
    many_related_fields = {
        'candidate_skills': 'candidate_contact',
        'tag_rels': 'candidate_contact',
    }

    def create(self, validated_data):
        contact = validated_data.get('contact', None)
        if not isinstance(contact, Contact):
            raise exceptions.ValidationError(
                _('Contact is required')
            )

        if models.CandidateContact.objects.filter(contact=contact).exists():
            raise exceptions.ValidationError(
                _('Candidate Contact with this Contact already exists.')
            )

        instance = super().create(validated_data)
        return instance

    class Meta:
        model = models.CandidateContact
        fields = ('__all__', {
            'tag_rels': ('id', 'verified_by', 'verification_evidence'),
            'candidate_skills': ('id', 'skill', 'score', 'prior_experience'),
            'contact': ('__all__', {
                'address': ('__all__', ),
            }),
        })
        related = RELATED_DIRECT

    def get_state(self, obj):
        if not obj:
            return

        states = obj.get_active_states()

        return [
            state.state.name_after_activation or
            state.state.name_before_activation
            for state in states
        ]

    def get_total_score(self, obj):
        if not obj:
            return

        return obj.get_total_score()

    def get_bmi(self, obj):
        if not obj:
            return

        return obj.get_bmi()

    def get_skill_list(self, obj):
        if not obj:
            return

        return ', '.join(obj.candidate_skills.all().values_list(
            'skill__name', flat=True)
        )

    def get_tag_list(self, obj):
        if not obj:
            return

        return ', '.join(obj.tag_rels.all().values_list(
            'tag__name', flat=True)
        )


class CandidateContactRegisterSerializer(ContactRegisterSerializer):

    candidate = CandidateContactSerializer(required=False)
    agree = serializers.BooleanField(required=True)
    is_subcontractor = serializers.BooleanField(required=False)
    tags = serializers.PrimaryKeyRelatedField(
        required=True,
        queryset=Tag.objects,
        many=True
    )
    skills = serializers.PrimaryKeyRelatedField(
        required=True,
        queryset=Skill.objects,
        many=True
    )

    def create(self, validated_data):
        candidate = validated_data.pop('candidate', {})
        agree = validated_data.pop('agree', False)
        tags = validated_data.pop('tags', []) or []
        skills = validated_data.pop('skills', []) or []

        if not agree:
            raise exceptions.ValidationError(_('You should agree'))

        contact = super().create(validated_data)

        candidate['contact'] = contact
        candidate_contact = CandidateContactSerializer().create(candidate)

        for tag in tags:
            models.TagRel.objects.create(
                candidate_contact=candidate_contact,
                tag=tag,
            )

        for skill in skills:
            models.SkillRel.objects.create(
                candidate_contact=candidate_contact,
                skill=skill,
            )

        return candidate_contact

    class Meta:
        fields = (
            'title', 'first_name', 'birthday', 'email', 'phone_mobile', 'tags',
            'last_name', 'picture', 'agree', 'skills', 'is_subcontractor',
            {
                'address': ('country', 'state', 'city', 'street_address',
                            'postal_code'),
                'candidate': ('tax_file_number', )
            },
        )


class SubcontractorSerializer(ApiBaseModelSerializer):

    class Meta:
        fields = '__all__'
        model = models.Subcontractor
