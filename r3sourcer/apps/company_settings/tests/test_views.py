import json

from django.core.urlresolvers import reverse
from rest_framework import status

from r3sourcer.apps.company_settings.models import CompanySettings
from r3sourcer.apps.core.models import InvoiceRule
from r3sourcer.apps.hr.models import PayslipRule


class TestCompanySettingsView:
    def test_get_company_settings(self, client, company, user, invoice_rule, payslip_rule):
        company_settings = company.company_settings
        company_settings.logo = '/logo/url'
        company_settings.color_scheme = 'color_scheme'
        company_settings.font = 'font'
        company_settings.forwarding_number = '+12345678901'
        company_settings.save()
        url = reverse('company_settings', kwargs={'version': 'v2'})
        client.force_login(user)
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['payslip_rule']['id'] == str(payslip_rule.id)
        assert response.data['payslip_rule']['period'] == payslip_rule.period
        assert response.data['company_settings']['forwarding_number'] == company_settings.forwarding_number
        assert response.data['company_settings']['color_scheme'] == company_settings.color_scheme
        assert response.data['company_settings']['font'] == company_settings.font
        assert response.data['company_settings']['id'] == company_settings.id
        assert response.data['company_settings']['logo'] == company_settings.logo.url
        assert response.data['invoice_rule']['separation_rule'] == invoice_rule.separation_rule
        assert response.data['invoice_rule']['show_candidate_name'] == invoice_rule.show_candidate_name
        assert response.data['invoice_rule']['id'] == str(invoice_rule.id)
        assert response.data['invoice_rule']['period'] == invoice_rule.period

    def test_update_company_settings(self, client, company, user, invoice_rule, payslip_rule):
        data = {
            'payslip_rule': {
                'period': 'fortnightly'
            },
            'company_settings': {
                'font': 'new_font'
            },
            'invoice_rule': {
                'period': 'fortnightly'
            }
        }
        url = reverse('company_settings', kwargs={'version': 'v2'})
        client.force_login(user)
        response = client.post(url, data=json.dumps(data), content_type='application/json')
        payslip_rule_new = PayslipRule.objects.get(id=payslip_rule.id)
        invoice_rule_new = InvoiceRule.objects.get(id=invoice_rule.id)
        company_settings_new = CompanySettings.objects.get(id=company.company_settings.id)

        assert response.status_code == status.HTTP_200_OK
        assert invoice_rule.period != invoice_rule_new.period
        assert payslip_rule.period != payslip_rule_new.period
        assert company.company_settings.font != company_settings_new.font
        assert invoice_rule_new.period == data['invoice_rule']['period']
        assert payslip_rule_new.period == data['payslip_rule']['period']
        assert company_settings_new.font == data['company_settings']['font']
