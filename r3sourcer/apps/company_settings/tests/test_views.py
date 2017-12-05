import json
import mock
import pytest

from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import force_authenticate

from r3sourcer.apps.company_settings.models import CompanySettings, AccountSet, MYOBAccount
from r3sourcer.apps.company_settings.views import CompanyGroupListView, CompanyGroupCreateView
from r3sourcer.apps.company_settings.models import GlobalPermission
from r3sourcer.apps.core.models import User, CompanyContact, CompanyContactRelationship, InvoiceRule
from r3sourcer.apps.hr.models import PayslipRule
from r3sourcer.apps.myob.models import MYOBCompanyFile, MYOBCompanyFileToken, MYOBAuthData


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


class TestCompanyFileAccountsView:
    def test_get_myob_account_list(self, client, user, company_file):
        account1 = MYOBAccount.objects.create(number='1-1000',
                                              name='Test Expense Account',
                                              type='expense',
                                              company_file=company_file)
        account2 = MYOBAccount.objects.create(number='2-2000',
                                              name='Test Income Account',
                                              type='income',
                                              company_file=company_file)
        url = reverse('company_file_accounts', kwargs={'version': 'v2', 'id': company_file.id})
        client.force_login(user)
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['myob_accounts'][1]['id'] == account1.id
        assert response.data['myob_accounts'][1]['number'] == account1.number
        assert response.data['myob_accounts'][1]['name'] == account1.name
        assert response.data['myob_accounts'][1]['type'] == account1.type
        assert response.data['myob_accounts'][0]['id'] == account2.id
        assert response.data['myob_accounts'][0]['number'] == account2.number
        assert response.data['myob_accounts'][0]['name'] == account2.name
        assert response.data['myob_accounts'][0]['type'] == account2.type


class TestMYOBAuthorizationView:
    @pytest.mark.django_db
    @mock.patch('r3sourcer.apps.myob.api.wrapper.MYOBAuth.retrieve_access_token')
    def test_authorization_success(self, mocked_function, client):
        data = {
            'api_key': 'qwe',
            'api_secret': 'api_secret',
            'redirect_uri': 'redirect_uri',
        }
        url = reverse('myob_authorization', kwargs={'version': 'v2'}) + "?code=code"
        response = client.post(url, data=data)

        assert response.status_code == status.HTTP_200_OK

    def test_authorization_fail(self, client, user):
        data = {
            'api_key': 'qwe',
            'api_secret': 'api_secret',
            'redirect_uri': 'redirect_uri',
        }
        url = reverse('myob_authorization', kwargs={'version': 'v2'}) + "?code=code"
        response = client.post(url, data=data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestUserGlobalPermissionListView:
    def test_get_user_permissions(self, client, user):
        permission = GlobalPermission.objects.create(name='permission_name', codename='permission_codename')
        permission2 = GlobalPermission.objects.create(name='permission_name2', codename='permission_codename2')
        user.user_permissions.add(permission, permission2)
        url = reverse('user_global_permission_list', kwargs={'version': 'v2', 'id': user.id})
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['permission_list'][0]['id'] == permission.id
        assert response.data['permission_list'][0]['name'] == permission.name
        assert response.data['permission_list'][0]['codename'] == permission.codename
        assert response.data['permission_list'][1]['id'] == permission2.id
        assert response.data['permission_list'][1]['name'] == permission2.name
        assert response.data['permission_list'][1]['codename'] == permission2.codename


class TestGroupGlobalPermissionListView:
    def test_get_group_permissions(self, client, group):
        permission = GlobalPermission.objects.create(name='permission_name', codename='permission_codename')
        permission2 = GlobalPermission.objects.create(name='permission_name2', codename='permission_codename2')
        group.permissions.add(permission, permission2)
        url = reverse('group_global_permission_list', kwargs={'version': 'v2', 'id': group.id})
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['permission_list'][0]['id'] == permission.id
        assert response.data['permission_list'][0]['name'] == permission.name
        assert response.data['permission_list'][0]['codename'] == permission.codename
        assert response.data['permission_list'][1]['id'] == permission2.id
        assert response.data['permission_list'][1]['name'] == permission2.name
        assert response.data['permission_list'][1]['codename'] == permission2.codename


class TestSetGroupGlobalPermissionView:
    def test_set_group_permission(self, client, group):
        permission = GlobalPermission.objects.create(name='permission_name', codename='permission_codename')
        permission2 = GlobalPermission.objects.create(name='permission_name2', codename='permission_codename2')
        url = reverse('set_group_global_permission', kwargs={'version': 'v2', 'id': group.id})
        payload = {
            'permission_list': [permission.id, permission2.id]
        }
        response = client.post(url, data=json.dumps(payload), content_type="application/json")
        result_permissions = group.permissions.all()

        assert response.status_code == status.HTTP_200_OK
        assert result_permissions[0] == permission
        assert result_permissions[1] == permission2


class TestSetUserGlobalPermissionView:
    def test_set_user_permission(self, client, user):
        permission = GlobalPermission.objects.create(name='permission_name', codename='permission_codename')
        permission2 = GlobalPermission.objects.create(name='permission_name2', codename='permission_codename2')
        url = reverse('set_user_global_permission', kwargs={'version': 'v2', 'id': user.id})
        payload = {
            'permission_list': [permission.id, permission2.id]
        }
        response = client.post(url, data=json.dumps(payload), content_type="application/json")
        result_permissions = user.user_permissions.all()

        assert response.status_code == status.HTTP_200_OK
        assert result_permissions[0] == permission
        assert result_permissions[1] == permission2


class TestGlobalPermissionListView:
    @pytest.mark.skip(reason='complete it when permission datamigration is done')
    def test_get_permission_list(self, client):
        permission = GlobalPermission.objects.create(name='permission_name', codename='permission_codename')
        permission2 = GlobalPermission.objects.create(name='permission_name2', codename='permission_codename2')
        url = reverse('global_permission_list', kwargs={'version': 'v2'})
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['permission_list'][0]['id'] == permission.id
        assert response.data['permission_list'][0]['name'] == permission.name
        assert response.data['permission_list'][0]['codename'] == permission.codename
        assert response.data['permission_list'][1]['id'] == permission2.id
        assert response.data['permission_list'][1]['name'] == permission2.name
        assert response.data['permission_list'][1]['codename'] == permission2.codename


class TestCompanyGroupListView:
    def test_list_company_group(self, group_with_permissions, rf, company):
        user = company.get_user()
        company.groups.add(group_with_permissions)
        url = reverse('company_group_list', kwargs={'version': 'v2'})
        request = rf.get(url)
        force_authenticate(request, user=user)
        response = CompanyGroupListView.as_view()(request)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['results'][0]['id'] == group_with_permissions.id
        assert len(response.data['results'][0]['permissions']) == 2
        assert 'id' in response.data['results'][0]['permissions'][0]
        assert 'name' in response.data['results'][0]['permissions'][0]
        assert 'codename' in response.data['results'][0]['permissions'][0]


class TestAddUserToGroupView:
    def test_add_user_to_group(self, user, group, client):
        data = {
            'user_id': user.id
        }
        url = reverse('add_user_to_group', kwargs={'version': 'v2', 'id': group.id})
        response = client.post(url, data=data)

        assert response.status_code == status.HTTP_200_OK
        assert user in group.user_set.all()


class TestRemoveUserFromGroupView:
    def test_remove_user_from_group(self, user, group, client):
        group.user_set.add(user)
        data = {
            'user_id': user.id
        }
        url = reverse('remove_user_from_group', kwargs={'version': 'v2', 'id': group.id})
        response = client.post(url, data=data)

        assert response.status_code == status.HTTP_200_OK
        assert user not in group.user_set.all()


class TestCompanyGroupCreateView:
    def test_create_company_group(self, company, rf):
        user = company.get_user()
        data = {
            "name": 'group_name'
        }
        url = reverse('company_group_create', kwargs={'version': 'v2'})
        request = rf.post(url, data=data)
        force_authenticate(request, user=user)
        response = CompanyGroupCreateView.as_view()(request)

        assert response.status_code == status.HTTP_201_CREATED
        assert company.groups.count() == 1
        assert company.groups.first().name == data['name']


class TestRevokeGroupGlobalPermissionView:
    def test_revoke_group_permission(self, group_with_permissions, client):
        permission_ids = group_with_permissions.permissions.all().values_list('id', flat=True)
        data = {
            "permission_list": list(permission_ids)
        }
        url = reverse('revoke_group_global_permission', kwargs={'version': 'v2', 'id': group_with_permissions.id})
        response = client.post(url, data=data)

        assert response.status_code == status.HTTP_200_OK
        assert len(group_with_permissions.permissions.all()) == 0

    def test_empty_permission_list(self, group, client):
        data = {
            "permission_list": list()
        }
        url = reverse('revoke_group_global_permission', kwargs={'version': 'v2', 'id': group.id})
        response = client.post(url, data=data)

        assert response.status_code == 400
        assert 'Ensure this field has at least 1 elements.' in response.data['errors']['permission_list']

    def test_nonexistent_permission(self, client, group):
        last_permission = GlobalPermission.objects.all().order_by('-id')[0]
        data = {
            "permission_list": [last_permission.id+1]
        }
        url = reverse('revoke_group_global_permission', kwargs={'version': 'v2', 'id': group.id})
        response = client.post(url, data=data)

        assert response.status_code == 400
        assert 'Some permissions dont exist.' in response.data['errors']['permission_list']


class TestRevokeUserGlobalPermissionView:
    def test_revoke_user_permission(self, user, client):
        permission = GlobalPermission.objects.create(name='permission_name', codename='permission_codename')
        user.user_permissions.add(permission)
        permission_ids = user.user_permissions.all().values_list('id', flat=True)
        data = {
            "permission_list": list(permission_ids)
        }
        url = reverse('revoke_user_global_permission', kwargs={'version': 'v2', 'id': user.id})
        response = client.post(url, data=data)

        assert response.status_code == status.HTTP_200_OK
        assert len(user.user_permissions.all()) == 0

    def test_empty_permission_list(self, user, client):
        data = {
            "permission_list": list()
        }
        url = reverse('revoke_user_global_permission', kwargs={'version': 'v2', 'id': user.id})
        response = client.post(url, data=data)

        assert response.status_code == 400
        assert 'Ensure this field has at least 1 elements.' in response.data['errors']['permission_list']

    def test_nonexistent_permission(self, client, user):
        last_permission = GlobalPermission.objects.all().order_by('-id')[0]
        data = {
            "permission_list": [last_permission.id+1]
        }
        url = reverse('revoke_user_global_permission', kwargs={'version': 'v2', 'id': user.id})
        response = client.post(url, data=data)

        assert response.status_code == 400
        assert 'Some permissions dont exist.' in response.data['errors']['permission_list']


class TestCompanyGroupDeleteView:
    def test_delete_group(self, group, client):
        group_id = group.id
        url = reverse('company_group_delete', kwargs={'version': 'v2', 'id': group_id})
        response = client.get(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Group.objects.filter(id=group_id).count() == 0


class TestCompanyUserListView:
    @pytest.mark.django_db
    def test_get_user_list(self, company, client):
        user1 = User.objects.create_user(email='test1@test.tt', phone_mobile='+12345678902', password='test1234')
        user2 = User.objects.create_user(email='test2@test.tt', phone_mobile='+12345678903', password='test1234')
        user3 = User.objects.create_user(email='test3@test.tt', phone_mobile='+12345678904', password='test1234')
        user1.contact.first_name = 'John'
        user1.contact.last_name = 'Doe'
        user1.contact.save()
        user2.contact.first_name = 'John'
        user2.contact.last_name = 'Doe'
        user2.contact.save()
        user3.contact.first_name = 'John'
        user3.contact.last_name = 'Doe'
        user3.contact.save()
        company_contact1 = CompanyContact.objects.create(contact=user1.contact)
        company_contact2 = CompanyContact.objects.create(contact=user2.contact)
        company_contact3 = CompanyContact.objects.create(contact=user3.contact)
        CompanyContactRelationship.objects.create(company=company, company_contact=company_contact1)
        CompanyContactRelationship.objects.create(company=company, company_contact=company_contact2)
        CompanyContactRelationship.objects.create(company=company, company_contact=company_contact3)

        url = reverse('company_users_list', kwargs={'version': 'v2'})
        client.force_login(company.manager.contact.user)
        response = client.get(url)

        assert response.status_code == 200
        assert len(response.data['user_list']) == 3
        assert response.data['user_list'][0]['id'] == str(user1.id)
        assert response.data['user_list'][0]['name'] == user1.get_full_name()
        assert response.data['user_list'][1]['id'] == str(user2.id)
        assert response.data['user_list'][1]['name'] == user2.get_full_name()
        assert response.data['user_list'][2]['id'] == str(user3.id)
        assert response.data['user_list'][2]['name'] == user3.get_full_name()


class TestUserGroupListView:
    def test_get_groups_of_user(self, client, user):
        group1 = Group.objects.create(name='group1')
        group2 = Group.objects.create(name='group2')
        user.groups.add(group1, group2)
        url = reverse('user_group_list', kwargs={'version': 'v2', 'id': user.id})
        client.force_login(user)
        response = client.get(url)

        assert response.data['results'][0]['id'] == group1.id
        assert response.data['results'][0]['name'] == group1.name
        assert response.data['results'][1]['id'] == group2.id
        assert response.data['results'][1]['name'] == group2.name


class TestUserCompanyFilesView:
    def test_company_file_list(self, client, user, company):
        auth_data = MYOBAuthData.objects.create(client_id='client_id',
                                                client_secret='client_secret',
                                                access_token='access_token',
                                                refresh_token='refresh_token',
                                                myob_user_uid='myob_user_uid',
                                                myob_user_username='myob_user_username',
                                                expires_in=1000,
                                                expires_at=timezone.now())
        company_file = MYOBCompanyFile.objects.create(cf_id='cf_id',
                                                      cf_uri='cf_uri',
                                                      cf_name='cf_name')
        MYOBCompanyFileToken.objects.create(company_file=company_file,
                                            auth_data=auth_data,
                                            company=company,
                                            cf_token='cf_token')
        url = reverse('user_company_files', kwargs={'version': 'v2'})
        client.force_login(user)
        response = client.get(url)

        assert len(response.data['company_files']) == 1
        assert response.data['company_files'][0]['id'] == company_file.cf_id
        assert response.data['company_files'][0]['uri'] == company_file.cf_uri
        assert response.data['company_files'][0]['name'] == company_file.cf_name
        assert response.data['company_files'][0]['authenticated'] == company_file.authenticated


class TestRefreshCompanyFilesView:
    @mock.patch('r3sourcer.apps.myob.api.wrapper.MYOBClient.get_company_files')
    def test_refresh_company_files(self, get_company_files, client, user, company, company_file_token):
        client.force_login(user)
        url = reverse('refresh_company_files', kwargs={'version': 'v2'})
        client.get(url)

        assert get_company_files.called


class TestCheckCompanyFilesView:
    @mock.patch('r3sourcer.apps.myob.api.wrapper.MYOBClient.check_company_file')
    def test_check_company_file(self, check_company_file, client, user, company, company_file_token):
        check_company_file.return_value = True
        company_file_id = company_file_token.company_file.cf_id
        url = reverse('check_company_files', kwargs={'version': 'v2'})
        payload = {
            'id': company_file_id,
            'username': '',
            'password': ''
        }
        client.force_login(user)
        client.post(url, data=json.dumps(payload), content_type="application/json")

        assert check_company_file.called
        assert MYOBCompanyFile.objects.get(cf_id=company_file_token.company_file.cf_id).authenticated
