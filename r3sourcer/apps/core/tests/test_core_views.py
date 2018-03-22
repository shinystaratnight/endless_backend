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
