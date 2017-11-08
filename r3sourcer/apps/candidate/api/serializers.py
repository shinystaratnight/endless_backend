from rest_framework import exceptions, serializers
from django.utils.translation import ugettext_lazy as _

from r3sourcer.apps.hr import models as hr_models
from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.skills import models as skill_models
from r3sourcer.apps.candidate import models as candidate_models
from r3sourcer.apps.core.api import serializers as core_serializers
from r3sourcer.apps.hr.api.serializers import timesheet as timesheet_serializers
from r3sourcer.apps.activity.endpoints import serializers as activity_serializers


class FavouriteListSerializer(core_serializers.ApiBaseModelSerializer):
    class Meta:
        model = hr_models.FavouriteList
        fields = '__all__'


class BlackListSerializer(core_serializers.ApiBaseModelSerializer):
    class Meta:
        model = hr_models.BlackList
        fields = '__all__'


class VacancyOfferSerializer(core_serializers.ApiBaseModelSerializer):
    class Meta:
        model = hr_models.VacancyOffer
        fields = '__all__'


class CarrierListSerializer(core_serializers.ApiBaseModelSerializer):
    class Meta:
        model = hr_models.CarrierList
        fields = '__all__'


class SkillRelSerializer(core_serializers.ApiBaseModelSerializer):
    class Meta:
        model = candidate_models.SkillRel
        fields = '__all__'


class TagRelSerializer(core_serializers.ApiBaseModelSerializer):
    class Meta:
        model = candidate_models.TagRel
        fields = '__all__'


class CandidateContactSerializer(core_serializers.ApiRealtedFieldManyMixin, core_serializers.ApiBaseModelSerializer):
    blacklist = BlackListSerializer(many=True)
    candidate_skills = SkillRelSerializer(many=True)
    tag_rels = TagRelSerializer(many=True)
    notes = serializers.NoteSerializer(many=True)
    active_states = serializers.WorkflowObjectSerializer(many=True)
    activities = activity_serializers.ActivitySerializer(many=True)
    favourites = FavouriteListSerializer(many=True)
    vacancy_offers = VacancyOfferSerializer(many=True)
    carrier_lists = CarrierListSerializer(many=True)
    candidate_evaluations = timesheet_serializers.CandidateEvaluationSerializer(many=True)

    method_fields = ('state', 'total_score', 'bmi', 'skill_list', 'tag_list')
    many_related_fields = {
        'candidate_evaluations': 'candidate_contact',
        'carrier_lists': 'candidate_contact',
        'vacancy_offers': 'candidate_contact',
        'active_states': 'candidate_contact',
        'blacklists': 'candidate_contact',
        'activities': 'candidate_contact',
        'notes': 'candidate_contact',
        'candidate_skills': 'candidate_contact',
        'tag_rels': 'candidate_contact',
        'favourites': 'candidate_contact',
    }

    def create(self, validated_data):
        contact = validated_data.get('contact', None)
        if not isinstance(contact, core_models.Contact):
            raise exceptions.ValidationError(
                _('Contact is required')
            )

        if candidate_models.CandidateContact.objects.filter(contact=contact).exists():
            raise exceptions.ValidationError(
                _('Candidate Contact with this Contact already exists.')
            )

        instance = super().create(validated_data)
        return instance

    class Meta:
        model = candidate_models.CandidateContact
        fields = ('__all__', {
            'blacklists': ('__all__',),
            'favourites': ('__all__',),
            'active_states': ('__all__',),
            'vacancy_offers': ('__all__',),
            'carrier_lists': ('__all__',),
            'candidate_evaluations': ('__all__',),
            'notes': ('id', 'note'),
            'activities': ('id', 'starts_at', 'ends_at', 'done', 'template', {
                'contact': ('__all__', {
                    'address': ('__all__',),
                },)
            }),
            'tag_rels': ('id', 'verified_by', 'verification_evidence'),
            'candidate_skills': (
                'id', 'skill', 'score', 'prior_experience'
            ),
            'contact': ('__all__', {
                'address': ('__all__',),
            }),
            'recruitment_agent': ('__all__', {
                'contact': ('__all__',),
            }),
        })

        related = core_serializers.RELATED_DIRECT

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
