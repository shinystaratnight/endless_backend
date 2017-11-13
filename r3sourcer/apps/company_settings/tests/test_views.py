import json

from django.core.urlresolvers import reverse
from rest_framework import status

from r3sourcer.apps.company_settings.models import CompanySettings, AccountSet, MYOBAccount
from r3sourcer.apps.core.models import InvoiceRule
from r3sourcer.apps.hr.models import PayslipRule


class TestCompanySettingsView:
    def test_get_company_settings(self, client, company, user, invoice_rule, payslip_rule, myob_account):
        company_settings = company.company_settings
        company_settings.logo = '/logo/url'
        company_settings.color_scheme = 'color_scheme'
        company_settings.font = 'font'
        company_settings.forwarding_number = '+12345678901'
        company_settings.save()
        account_set = company_settings.account_set
        account_set.subcontractor_contract_work = myob_account
        account_set.subcontractor_gst = myob_account
        account_set.candidate_wages = myob_account
        account_set.candidate_superannuation = myob_account
        account_set.company_client_labour_hire = myob_account
        account_set.company_client_gst = myob_account
        account_set.save()
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
        assert response.data['account_set']['subcontractor_contract_work']['id'] == account_set.subcontractor_contract_work.id
        assert response.data['account_set']['subcontractor_gst']['id'] == account_set.subcontractor_gst.id
        assert response.data['account_set']['candidate_wages']['id'] == account_set.candidate_wages.id
        assert response.data['account_set']['candidate_superannuation']['id'] == account_set.candidate_superannuation.id
        assert response.data['account_set']['company_client_labour_hire']['id'] == account_set.company_client_labour_hire.id
        assert response.data['account_set']['company_client_gst']['id'] == account_set.company_client_gst.id

    def test_update_company_settings(self, client, company, user, invoice_rule, payslip_rule, myob_account):
        data = {
            'payslip_rule': {
                'period': 'fortnightly'
            },
            'company_settings': {
                'font': 'new_font'
            },
            'invoice_rule': {
                'period': 'fortnightly'
            },
            'account_set': {
                'subcontractor_contract_work': {
                    'id': myob_account.id,
                },
                'subcontractor_gst': {
                    'id': myob_account.id,
                },
                'candidate_wages': {
                    'id': myob_account.id,
                },
                'candidate_superannuation': {
                    'id': myob_account.id,
                },
                'company_client_labour_hire': {
                    'id': myob_account.id,
                },
                'company_client_gst': {
                    'id': myob_account.id,
                }
            }
        }
        url = reverse('company_settings', kwargs={'version': 'v2'})
        client.force_login(user)
        response = client.post(url, data=json.dumps(data), content_type='application/json')
        payslip_rule_new = PayslipRule.objects.get(id=payslip_rule.id)
        invoice_rule_new = InvoiceRule.objects.get(id=invoice_rule.id)
        company_settings_new = CompanySettings.objects.get(id=company.company_settings.id)
        account_set_new = AccountSet.objects.get(id=company.company_settings.account_set.id)

        assert response.status_code == status.HTTP_200_OK
        assert invoice_rule.period != invoice_rule_new.period
        assert payslip_rule.period != payslip_rule_new.period
        assert company.company_settings.font != company_settings_new.font
        assert invoice_rule_new.period == data['invoice_rule']['period']
        assert payslip_rule_new.period == data['payslip_rule']['period']
        assert company_settings_new.font == data['company_settings']['font']
        assert account_set_new.subcontractor_contract_work == myob_account
        assert account_set_new.subcontractor_gst == myob_account
        assert account_set_new.candidate_wages == myob_account
        assert account_set_new.candidate_superannuation == myob_account
        assert account_set_new.company_client_labour_hire == myob_account
        assert account_set_new.company_client_gst == myob_account


class TestMYOBAccountListView:
    def test_get_myob_account_list(self, client, user):
        account1 = MYOBAccount.objects.create(number='1-1000',
                                              name='Test Expense Account',
                                              type='expense')
        account2 = MYOBAccount.objects.create(number='2-2000',
                                              name='Test Income Account',
                                              type='income')
        url = reverse('myob_accounts', kwargs={'version': 'v2'})
        client.force_login(user)
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['myob_accounts'][0]['id'] == account1.id
        assert response.data['myob_accounts'][0]['number'] == account1.number
        assert response.data['myob_accounts'][0]['name'] == account1.name
        assert response.data['myob_accounts'][0]['type'] == account1.type
        assert response.data['myob_accounts'][1]['id'] == account2.id
        assert response.data['myob_accounts'][1]['number'] == account2.number
        assert response.data['myob_accounts'][1]['name'] == account2.name
        assert response.data['myob_accounts'][1]['type'] == account2.type
