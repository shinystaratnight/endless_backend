import mock

from django.core.urlresolvers import reverse
from rest_framework import status

from r3sourcer.apps.core.models import Invoice


class TestApproveInvoiceView:

    @mock.patch('r3sourcer.apps.core.views.sync_invoice')
    def test_get_user_permissions(self, mock_sync, client, invoice):
        invoice.approved = False
        invoice.save()

        url = reverse('approve_invoice', kwargs={'version': 'v2', 'id': invoice.id})
        response = client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert invoice.approved is False
        assert Invoice.objects.get(id=invoice.id).approved is True


class TestUserRolesView:
    def test_get(self, client, user, roles):
        user.role.add(*roles)
        user.save()
        url = reverse('user_roles', kwargs={'version': 'v2'})
        client.force_login(user)
        response = client.get(url).json()

        assert 'manager' in response['roles']
        assert 'candidate' in response['roles']
        assert 'client' in response['roles']


class TestSetRolesView:
    def test_set_role(self, client, user, roles):
        data = {
            'roles': ['candidate']
        }
        url = reverse('set_roles', kwargs={'version': 'v2', 'id': user.id})
        client.force_login(user)
        client.post(url, data=data)

        assert user.role.first().name == 'candidate'


class TestRevokeRolesView:
    def test_revoke_role(self, client, user, roles):
        user.role.add(*roles)
        data = {
            'roles': ['candidate']
        }
        url = reverse('revoke_roles', kwargs={'version': 'v2', 'id': user.id})
        client.force_login(user)
        client.post(url, data=data)
        roles = [x.name for x in user.role.all()]

        assert 'candidate' not in roles
