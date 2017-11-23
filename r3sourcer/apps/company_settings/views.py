from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import APIView

from r3sourcer.apps.company_settings import serializers
from r3sourcer.apps.company_settings.models import MYOBAccount
from r3sourcer.apps.myob.api.wrapper import MYOBAuth


class CompanySettingsView(APIView):
    def get(self, *args, **kwargs):
        company = self.request.user.contact.company_contact.first().companies.first()

        if not company:
            raise exceptions.APIException("User has no relation to any company.")

        company_settings = company.company_settings
        invoice_rule = company.invoice_rules.first()
        payslip_rule = company.payslip_rules.first()
        account_set = company.company_settings.account_set

        company_settings_serializer = serializers.CompanySettingsSerializer(company_settings)
        invoice_rule_serializer = serializers.InvoiceRuleSerializer(invoice_rule)
        payslip_rule_serializer = serializers.PayslipRuleSerializer(payslip_rule)
        account_set_serializer = serializers.AccountSetSerializer(account_set)

        data = {
            "company_settings": company_settings_serializer.data,
            "invoice_rule": invoice_rule_serializer.data,
            "payslip_rule": payslip_rule_serializer.data,
            "account_set": account_set_serializer.data
        }

        return Response(data)

    def post(self, *args, **kwargs):
        company = self.request.user.contact.company_contact.first().companies.first()

        if not company:
            raise exceptions.APIException("User has no relation to any company.")

        if 'company_settings' in self.request.data:
            serializer = serializers.CompanySettingsSerializer(company.company_settings,
                                                               data=self.request.data['company_settings'],
                                                               partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        if 'invoice_rule' in self.request.data:
            serializer = serializers.InvoiceRuleSerializer(company.invoice_rules.first(),
                                                           data=self.request.data['invoice_rule'],
                                                           partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        if 'payslip_rule' in self.request.data:
            serializer = serializers.PayslipRuleSerializer(company.payslip_rules.first(),
                                                           data=self.request.data['payslip_rule'],
                                                           partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        if 'account_set' in self.request.data:
            serializer = serializers.AccountSetSerializer(company.company_settings.account_set,
                                                          data=self.request.data['account_set'],
                                                          partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return Response()


class MYOBAccountListView(APIView):
    def get(self, *args, **kwargs):
        myob_accounts = MYOBAccount.objects.all()
        serializer = serializers.MYOBAccountSerializer(myob_accounts, many=True)
        data = {
            'myob_accounts': serializer.data
        }

        return Response(data)


class MYOBAuthorizationView(APIView):
    """
    Accepts Developer Key and Developer Secret and checks if they are correct
    """
    def post(self, *args, **kwargs):
        data = {
            'client_id': self.request.data.get('api_key', None),
            'client_secret': self.request.data.get('api_secret', None),
            'refresh_token': self.request.data.get('redirect_uri', None),
            'grant_type': 'refresh_token'
        }
        auth_client = MYOBAuth(self.request)
        auth_client.retrieve_access_code()
        auth_client.retrieve_access_token(data=data)

        return Response()
