from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from r3sourcer.apps.core.models import Company
from r3sourcer.apps.core.api.serializers import ApiBaseModelSerializer

from ...models import TimeSheet, CandidateEvaluation


__all__ = [
    'TimeSheetSignatureSerializer',
    'PinCodeSerializer',
    'TimeSheetSerializer',
]


class ValidateApprovalScheme(serializers.Serializer):

    APPROVAL_SCHEME = None

    def validate(self, attrs):
        # get master companies and check existing
        companies = self.instance.supervisor.get_master_company()
        if len(companies) == 0:
            raise serializers.ValidationError(_("Supervisor has not master company"))

        company = companies[0]
        if company.timesheet_approval_scheme != self.APPROVAL_SCHEME:
            raise serializers.ValidationError(_("Incorrect approval scheme"))
        return attrs


class TimeSheetSignatureSerializer(ValidateApprovalScheme, serializers.ModelSerializer):

    APPROVAL_SCHEME = Company.TIMESHEET_APPROVAL_SCHEME.SIGNATURE

    class Meta:
        model = TimeSheet
        fields = ('supervisor_signature',)
        extra_kwargs = {'supervisor_signature': {
            'required': True,
            'allow_empty_file': False,
            'allow_null': False}
        }


class PinCodeSerializer(ValidateApprovalScheme):

    APPROVAL_SCHEME = Company.TIMESHEET_APPROVAL_SCHEME.PIN

    pin_code = serializers.CharField(min_length=4)

    def validate(self, attrs):
        attrs = super(PinCodeSerializer, self).validate(attrs)
        supervisor = self.instance.supervisor
        if supervisor.pin_code != attrs['pin_code']:
            raise serializers.ValidationError({'pin_code': _("Incorrect pin code")})
        return attrs


class TimeSheetSerializer(ApiBaseModelSerializer):

    method_fields = ('company', 'jobsite', 'position')

    class Meta:
        model = TimeSheet
        fields = '__all__'
        related_fields = {
            'vacancy_offer': ({
                'candidate_contact': ('id', {
                    'contact': ('picture', ),
                }, ),
            }, ),
        }

    def get_company(self, obj):
        if obj:
            return str(obj.get_closest_company())

    def get_jobsite(self, obj):
        if obj:
            return str(obj.vacancy_offer.vacancy.jobsite)

    def get_position(self, obj):
        if obj:
            return str(obj.vacancy_offer.vacancy.position)


class CandidateEvaluationSerializer(ApiBaseModelSerializer):

    class Meta:
        model = CandidateEvaluation
        fields = '__all__'
