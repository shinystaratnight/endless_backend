import json
import pytest

from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import force_authenticate

from r3sourcer.apps.company_settings.views import CompanyGroupListView, CompanyGroupCreateView
from r3sourcer.apps.company_settings.models import GlobalPermission
from r3sourcer.apps.core.models import User, CompanyContact, CompanyContactRelationship


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
