from rest_framework import serializers

from r3sourcer.apps.core.models import InvoiceRule
from r3sourcer.apps.hr.models import PayslipRule
from r3sourcer.apps.company_settings.models import CompanySettings


class CompanySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySettings
        fields = ('id', 'company', 'logo', 'color_scheme', 'font', 'forwarding_number')
        read_only_fields = ('company',)


class PayslipRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayslipRule
        fields = ('id', 'period')


class InvoiceRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceRule
        fields = ('id', 'period', 'separation_rule', 'show_candidate_name')
