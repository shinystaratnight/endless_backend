import mock
import pytest

from django.core.urlresolvers import reverse

from r3sourcer.apps.core.models import SiteCompany, Contact


@pytest.mark.django_db
class TestTrialUserView:

    def make_post_request(self, client, data=None):
        url = reverse('register_trial', kwargs={'version': 'v2'})
        return client.post(url, data=data)

    @mock.patch('r3sourcer.apps.core.api.views.send_trial_email')
    @mock.patch('r3sourcer.apps.core.api.views.cancel_trial')
    def test_register_success(self, mock_task, mock_cancel, client, contact_phone):
        data = {
            'first_name': 'testuser42',
            'last_name': 'tester42',
            'email': 'test42@test.tt',
            'phone_mobile': contact_phone,
            'company_name': 'Test Company',
            'website': 'test',
        }

        resp = self.make_post_request(client, data).json()

        assert resp['status'] == 'success'
        assert Contact.objects.filter(email='test42@test.tt', phone_mobile=contact_phone).exists()
        assert SiteCompany.objects.filter(site__domain='test.r3sourcer.com', company__name='Test Company').exists()
