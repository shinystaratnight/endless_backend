from crum import get_current_request
from django.db.models import Avg
from django.utils.translation import ugettext_lazy as _
from rest_framework import exceptions, serializers

from r3sourcer.apps.candidate import models as candidate_models
from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.core.api import serializers as core_serializers, mixins as core_mixins, fields as core_fields
from r3sourcer.apps.hr import models as hr_models
from r3sourcer.apps.skills import models as skill_models


class FavouriteListSerializer(core_serializers.ApiBaseModelSerializer):
    class Meta:
        model = hr_models.FavouriteList
        fields = '__all__'


class BlackListSerializer(core_serializers.ApiBaseModelSerializer):
    class Meta:
        model = hr_models.BlackList
        fields = '__all__'


class JobOfferSerializer(core_serializers.ApiBaseModelSerializer):
    class Meta:
        model = hr_models.JobOffer
        fields = '__all__'


class CarrierListSerializer(core_serializers.ApiBaseModelSerializer):
    class Meta:
        model = hr_models.CarrierList
        fields = '__all__'


class SkillRelSerializer(core_mixins.CreatedUpdatedByMixin, core_serializers.ApiBaseModelSerializer):
    class Meta:
        model = candidate_models.SkillRel
        fields = (
            '__all__',
            {
                'skill': ('id', 'name', '__str__'),
            },
        )

    def validate(self, data):
        skill = data.get('skill')

        is_lower = skill.lower_rate_limit and data.get('hourly_rate') < skill.lower_rate_limit
        is_upper = skill.upper_rate_limit and data.get('hourly_rate') > skill.upper_rate_limit
        if is_lower or is_upper:
            raise exceptions.ValidationError({
                'hourly_rate': _('Hourly rate should be between {lower_limit} and {upper_limit}').format(
                    lower_limit=skill.lower_rate_limit, upper_limit=skill.upper_rate_limit,
                )
            })

        return data


class TagRelSerializer(core_serializers.ApiBaseModelSerializer):
    class Meta:
        model = candidate_models.TagRel
        fields = (
            '__all__',
            {
                'tag': ('id', 'name', 'evidence_required_for_approval', 'active')
            }
        )

    def validate(self, data):
        if data.get('tag').evidence_required_for_approval and not data.get('verification_evidence'):
            raise serializers.ValidationError({'verification_evidence': _('Verification evidence is requred')})

        return data


class CandidateContactSerializer(
    core_serializers.ApiRelatedFieldManyMixin, core_mixins.WorkflowStatesColumnMixin,
    core_mixins.WorkflowLatestStateMixin, core_serializers.ApiBaseModelSerializer
):

    candidate_skills = SkillRelSerializer(many=True)
    tag_rels = TagRelSerializer(many=True)

    method_fields = ('average_score', 'bmi', 'skill_list', 'tag_list', 'workflow_score')
    many_related_fields = {
        'candidate_skills': 'candidate_contact',
        'tag_rels': 'candidate_contact',
    }

    def create(self, validated_data):
        contact = validated_data.get('contact', None)
        if not isinstance(contact, core_models.Contact):
            raise exceptions.ValidationError(
                _('Contact is required.')
            )

        if candidate_models.CandidateContact.objects.filter(contact=contact).exists():
            raise exceptions.ValidationError(
                _('Candidate Contact with this Contact already exists.')
            )

        if not contact.birthday:
            raise exceptions.ValidationError({'contact': _('Contact should have birthday.')})

        request = self.context.get('request')
        access_levels = (core_models.constants.MANAGER, core_models.constants.CLIENT)

        if request and (not request.user.is_authenticated or request.user.access_level not in access_levels):
            raise exceptions.PermissionDenied()

        instance = super().create(validated_data)

        if request:
            current_company = request.user.contact.get_closest_company()
            master_company = company.get_closest_master_company()
            candidate_models.CandidateRel.objects.create(
                master_company=master_company,
                candidate_contact=instance,
                company_contact=request.user.contact.company_contact.filter(relationships__active=True).first(),
                owner=True,
                active=True,
            )

        return instance

    class Meta:
        model = candidate_models.CandidateContact
        fields = (
            '__all__',
            {
                'contact': (
                    'id', 'first_name', 'last_name', 'email', 'phone_mobile', 'is_available', 'picture', 'gender', {
                        'address': ('__all__', ),
                    }
                ),
                'tag_rels': ('id', 'verification_evidence', {
                    'verified_by': ('id', ),
                    'tag': ('id', )
                }),
                'candidate_skills': ('id', 'score', 'prior_experience', {
                    'skill': ('id', )
                }),
                'candidate_scores': ('id', 'client_feedback', 'reliability', 'loyalty', 'recruitment_score'),
                'recruitment_agent': ('id', 'job_title', {
                    'contact': ('id', 'phone_mobile')
                })
            }
        )
        read_only_fields = ('candidate_scores',)

        related = core_serializers.RELATED_DIRECT

    def get_average_score(self, obj):
        if not obj:
            return

        return obj.candidate_scores.get_average_score()

    def get_bmi(self, obj):
        if not obj:
            return

        return obj.get_bmi()

    def get_skill_list(self, obj):
        if not obj:
            return

        return SkillRelSerializer(obj.candidate_skills.all(), many=True).data

    def get_tag_list(self, obj):
        if not obj:
            return

        return TagRelSerializer(obj.tag_rels.all(), many=True).data

    def get_workflow_score(self, obj):
        return obj.get_active_states().aggregate(score=Avg('score'))['score']


class CandidateContactRegisterSerializer(core_serializers.ContactRegisterSerializer):

    candidate = CandidateContactSerializer(required=False)
    agree = serializers.BooleanField(required=True)
    is_subcontractor = serializers.BooleanField(required=False)
    tags = serializers.PrimaryKeyRelatedField(
        required=True,
        queryset=core_models.Tag.objects,
        many=True
    )
    skills = serializers.PrimaryKeyRelatedField(
        required=True,
        queryset=skill_models.Skill.objects,
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
            candidate_models.TagRel.objects.create(
                candidate_contact=candidate_contact,
                tag=tag,
            )

        for skill in skills:
            candidate_models.SkillRel.objects.create(
                candidate_contact=candidate_contact,
                skill=skill,
                hourly_rate=0
            )

        return candidate_contact

    class Meta:
        fields = (
            'title', 'first_name', 'birthday', 'email', 'phone_mobile', 'tags',
            'last_name', 'picture', 'agree', 'skills', 'is_subcontractor',
            {
                'address': ('country', 'state', 'city', 'street_address', 'postal_code'),
                'candidate': ('tax_file_number', )
            },
        )


class SubcontractorSerializer(core_serializers.ApiBaseModelSerializer):
    class Meta:
        fields = '__all__'
        model = candidate_models.Subcontractor


class CandidatePoolSerializer(core_serializers.ApiBaseModelSerializer):

    method_fields = ('average_score', 'owned_by')

    class Meta:
        model = candidate_models.CandidateContactAnonymous
        fields = ('profile_price', 'id')

    def get_average_score(self, obj):
        return obj.candidate_scores.get_average_score()

    def get_owned_by(self, obj):
        return core_fields.ApiBaseRelatedField.to_read_only_data(obj.candidate_rels.get(owner=True).master_company)


class CandidateRelSerializer(core_serializers.ApiBaseModelSerializer):

    class Meta:
        fields = '__all__'
        model = candidate_models.CandidateRel
