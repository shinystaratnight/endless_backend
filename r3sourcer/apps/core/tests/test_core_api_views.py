import pytest

from django.core.urlresolvers import reverse


@pytest.mark.django_db
class TestTrialUserView:

    def make_post_request(self, client, data=None):
        url = reverse('register_trial', kwargs={'version': 'v2'})
        return client.post(url, data=data)

    def test_register_success(self, client, contact_phone):
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
