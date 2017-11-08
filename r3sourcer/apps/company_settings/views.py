from rest_framework.response import Response
from rest_framework.views import APIView

from r3sourcer.apps.company_settings import serializers


class CompanySettingsView(APIView):
    def get(self, *args, **kwargs):
        company = self.request.user.contact.company_contact.first().companies.first()
        company_settings = company.company_settings
        invoice_rule = company.invoice_rules.first()
        payslip_rule = company.payslip_rules.first()

        company_settings_serializer = serializers.CompanySettingsSerializer(company_settings)
        invoice_rule_serializer = serializers.InvoiceRuleSerializer(invoice_rule)
        payslip_rule_serializer = serializers.PayslipRuleSerializer(payslip_rule)

        data = {
            "company_settings": company_settings_serializer.data,
            "invoice_rule": invoice_rule_serializer.data,
            "payslip_rule": payslip_rule_serializer.data,
        }

        return Response(data)

    def post(self, *args, **kwargs):
        company = self.request.user.contact.company_contact.first().companies.first()
        company_settings_serializer = serializers.CompanySettingsSerializer(company.company_settings,
                                                                            data=self.request.data['company_settings'],
                                                                            partial=True)
        invoice_rule_serializer = serializers.InvoiceRuleSerializer(company.invoice_rules.first(),
                                                                    data=self.request.data['invoice_rule'],
                                                                    partial=True)
        payslip_rule_serializer = serializers.PayslipRuleSerializer(company.payslip_rules.first(),
                                                                    data=self.request.data['payslip_rule'],
                                                                    partial=True)
        company_settings_serializer.is_valid(raise_exception=True)
        invoice_rule_serializer.is_valid(raise_exception=True)
        payslip_rule_serializer.is_valid(raise_exception=True)
        company_settings_serializer.save()
        invoice_rule_serializer.save()
        payslip_rule_serializer.save()

        return Response()
