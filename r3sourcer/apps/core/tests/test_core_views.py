from django.core.urlresolvers import reverse
from rest_framework import status

from r3sourcer.apps.core.models import Invoice


class TestApproveInvoiceView:
    def test_get_user_permissions(self, client, invoice):
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
