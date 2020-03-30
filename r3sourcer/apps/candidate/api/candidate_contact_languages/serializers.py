from django.core.exceptions import ObjectDoesNotExist, ValidationError
from rest_framework import serializers

from r3sourcer.apps.candidate.models import CandidateContactLanguage, CandidateContact
from r3sourcer.apps.core.models import Language


class CandidateContactLanguageSerializer(serializers.ModelSerializer):
    language_id = serializers.CharField()
    candidate_contact_id = serializers.CharField()

    class Meta:
        model = CandidateContactLanguage
        fields = (
            'language_id',
            'candidate_contact_id',
            'default',
        )

    @classmethod
    def validate_language_id(cls, value):
        try:
            Language.objects.get(alpha_2=value)
        except ObjectDoesNotExist:
            raise ValidationError('Language with alpha_2 = {} does not exist'.format(value))
        return value

    @classmethod
    def validate_candidate_contact_id(cls, value):
        try:
            CandidateContact.objects.get(pk=value)
        except ObjectDoesNotExist:
            raise ValidationError('Candidate contact with pk = {} does not exist'.format(value))
        return value
