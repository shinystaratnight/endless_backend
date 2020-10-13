from decimal import Decimal

from django.db.models import Avg
from django.utils.translation import ugettext_lazy as _
from rest_framework import exceptions, serializers
from rest_framework.exceptions import ValidationError

from r3sourcer.apps.candidate import models as candidate_models
from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.core.api import serializers as core_serializers, mixins as core_mixins, fields as core_fields
from r3sourcer.apps.core.utils.companies import get_site_master_company
from r3sourcer.apps.core.utils.utils import normalize_phone_number
from r3sourcer.apps.hr import models as hr_models
from r3sourcer.apps.myob.models import MYOBSyncObject
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
                'skill': ('id', {'name': ('__str__', {'translations': ('language', 'value')})}, '__str__'),
            },
        )
        extra_kwargs = {
            'score': {'max_value': Decimal(5)},
        }

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
                'tag': ('id', 'name', 'evidence_required_for_approval', 'active', 'confidential',
                        {'translations': ('language', 'value')}),
                'verified_by': ('id', 'contact', 'job_title'),
            }
        )

    def validate(self, data):
        if data.get('tag').evidence_required_for_approval and not data.get('verification_evidence'):
            raise serializers.ValidationError({'verification_evidence': _('Verification evidence is requred')})

        return data


class CandidateContactSerializer(core_mixins.WorkflowStatesColumnMixin,
                                 core_mixins.WorkflowLatestStateMixin,
                                 core_mixins.ApiContentTypeFieldMixin,
                                 core_serializers.ApiBaseModelSerializer):

    emergency_contact_phone = serializers.CharField(allow_null=True, required=False)

    method_fields = ('average_score', 'bmi', 'skill_list', 'tag_list', 'workflow_score', 'master_company', 'myob_name')

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

        request = self.context.get('request')
        access_levels = (core_models.constants.MANAGER, core_models.constants.CLIENT)

        if request and (not request.user.is_authenticated or request.user.access_level not in access_levels):
            raise exceptions.PermissionDenied()

        instance = super().create(validated_data)

        if request:
            current_company = request.user.contact.get_closest_company()
            master_company = current_company.get_closest_master_company()
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
                    'id', 'first_name', 'last_name', 'email', 'phone_mobile', 'is_available', 'picture', 'gender',
                    'birthday', 'myob_card_id', 'old_myob_card_id',
                    {
                        'address': ('__all__', ),
                    }
                ),
                'candidate_scores': (
                    'id', 'client_feedback', 'reliability', 'loyalty', 'recruitment_score', 'skill_score'
                ),
                'recruitment_agent': ('id', 'job_title', {
                    'contact': ('id', 'phone_mobile')
                }),
                'superannuation_fund': ('id', 'product_name')
            }
        )
        read_only_fields = ('candidate_scores', 'old_myob_card_id')

        related = core_serializers.RELATED_DIRECT

    def validate_emergency_contact_phone(self, value):
        if value:
            master_company = get_site_master_company(request=self.context['request'])
            if not master_company:
                raise ValidationError(_('Master company not found'))
            country_code = master_company.get_hq_address().address.country.code2
            value = normalize_phone_number(value, country_code)
        return value

    def get_average_score(self, obj):
        if not obj:
            return
        if obj.candidate_scores:
            score = obj.candidate_scores.get_average_score()
        else:
            score = None
        return score and '{0:.3}'.format(score)

    def get_bmi(self, obj):
        if not obj:
            return

        return obj.get_bmi()

    def get_skill_list(self, obj):
        if not obj:
            return

        return SkillRelSerializer(obj.candidate_skills.all(), many=True, fields=['score', 'skill', 'id']).data

    def get_tag_list(self, obj):
        if not obj:
            return

        return TagRelSerializer(obj.tag_rels.all(), many=True, fields=['id', 'tag']).data

    def get_workflow_score(self, obj):
        return obj.get_active_states().aggregate(score=Avg('score'))['score']

    def get_master_company(self, obj):
        master_company = obj.get_closest_company()
        return master_company and core_fields.ApiBaseRelatedField.to_read_only_data(master_company)

    def get_myob_name(self, obj):
        sync_obj = self._get_sync_object(obj)
        return sync_obj and sync_obj.legacy_myob_card_number

    def _get_sync_object(self, obj):
        return MYOBSyncObject.objects.filter(record=obj.id).first()


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


class SubcontractorCandidateRelationSerializer(core_serializers.ApiBaseModelSerializer):
    class Meta:
        fields = ('id', 'subcontractor', 'candidate_contact')
        model = candidate_models.SubcontractorCandidateRelation


class CandidatePoolSerializer(core_mixins.WorkflowStatesColumnMixin, core_mixins.WorkflowLatestStateMixin,
                              core_serializers.ApiBaseModelSerializer):

    method_fields = ('average_score', 'owned_by', 'bmi', 'tag_list', 'skill_list')

    class Meta:
        model = candidate_models.CandidateContactAnonymous
        fields = ('profile_price', 'id', 'transportation_to_work', 'height',
                  'weight', 'nationality',
                  {
                      'candidate_scores': (
                            'id', 'client_feedback', 'reliability', 'loyalty', 'recruitment_score', 'skill_score'
                          ),
                      'contact': (
                          '__str__', 'is_available', 'picture', 'gender'
                          ),
                  }
                  )
        related = core_serializers.RELATED_DIRECT

    def get_average_score(self, obj):
        return obj.candidate_scores.get_average_score()

    def get_owned_by(self, obj):
        return core_fields.ApiBaseRelatedField.to_read_only_data(obj.candidate_rels.get(owner=True).master_company)

    def get_bmi(self, obj):
        if not obj:
            return

        return obj.get_bmi()

    def get_tag_list(self, obj):
        if not obj:
            return

        return TagRelSerializer(obj.tag_rels.all(), many=True, fields=['id', 'tag']).data

    def get_skill_list(self, obj):
        if not obj:
            return

        return SkillRelSerializer(obj.candidate_skills.all(), many=True, fields=['score', 'skill', 'id']).data


class CandidatePoolDetailSerializer(core_serializers.ApiBaseModelSerializer):

    method_fields = ('average_score', 'owned_by', 'bmi')

    class Meta:
        model = candidate_models.CandidateContactAnonymous
        fields = ('profile_price', 'id', 'updated_at', 'created_at', 'transportation_to_work', 'height',
                  'weight', 'residency', 'visa_type', 'visa_expiry_date', 'nationality',
                  'vevo_checked_at',
                  {
                      'candidate_scores': (
                            'id', 'client_feedback', 'reliability', 'loyalty', 'recruitment_score', 'skill_score'
                          ),
                      'contact': (
                          '__str__', 'is_available', 'picture',
                          ),
                  }
                  )

    def get_average_score(self, obj):
        return obj.candidate_scores.get_average_score()

    def get_owned_by(self, obj):
        return core_fields.ApiBaseRelatedField.to_read_only_data(obj.candidate_rels.get(owner=True).master_company)

    def get_bmi(self, obj):
        if not obj:
            return

        return obj.get_bmi()


class CandidateRelSerializer(core_serializers.ApiBaseModelSerializer):

    class Meta:
        fields = '__all__'
        model = candidate_models.CandidateRel
