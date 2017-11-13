from rest_framework import serializers

from r3sourcer.apps.core.models import InvoiceRule
from r3sourcer.apps.hr.models import PayslipRule
from r3sourcer.apps.company_settings.models import CompanySettings, AccountSet, MYOBAccount


class CompanySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySettings
        fields = ('id', 'logo', 'color_scheme', 'font', 'forwarding_number')
        read_only_fields = ('company',)


class PayslipRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayslipRule
        fields = ('id', 'period')


class InvoiceRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceRule
        fields = ('id', 'period', 'separation_rule', 'show_candidate_name')


class MYOBAccountSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()

    class Meta:
        model = MYOBAccount
        fields = ('id', 'number', 'name', 'type')


class AccountSetSerializer(serializers.ModelSerializer):
    subcontractor_contract_work = MYOBAccountSerializer()
    subcontractor_gst = MYOBAccountSerializer()
    candidate_wages = MYOBAccountSerializer()
    candidate_superannuation = MYOBAccountSerializer()
    company_client_labour_hire = MYOBAccountSerializer()
    company_client_gst = MYOBAccountSerializer()

    class Meta:
        model = AccountSet
        fields = ('subcontractor_contract_work', 'subcontractor_gst', 'candidate_wages', 'candidate_superannuation',
                  'company_client_labour_hire', 'company_client_gst')

    def update(self, instance, validated_data):
        fields = ('subcontractor_contract_work', 'subcontractor_gst', 'candidate_wages', 'candidate_superannuation',
                  'company_client_labour_hire', 'company_client_gst')

        for field in fields:
            if validated_data.get(field, None):
                myob_account = MYOBAccount.objects.filter(id=validated_data[field]['id']).first()

                if myob_account:
                    setattr(instance, field, myob_account)

        instance.save()
        return instance
