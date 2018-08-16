import json
import mock

import stripe

from django.core.urlresolvers import reverse

from r3sourcer.apps.billing.models import Subscription, Discount
from r3sourcer.apps.core.models import Company


class TestSubscriptionCreateView:
    @mock.patch.object(stripe.Plan, 'create')
    @mock.patch.object(stripe.Subscription, 'create')
    def test_post(self, mocked_plan, mocked_subscription, client, user, company, relationship):
        plan = mock.Mock()
        plan.id = 'plan_id'
        mocked_plan.return_value = plan
        subscription = mock.Mock()
        subscription.id = 'subscription_id'
        mocked_subscription.return_value = subscription

        company.stripe_customer = 'cus_CnGRCuSr6Fo0Uv'
        company.save()
        data = {
            "type": "monthly",
            "worker_count": 100,
            "price": 500
        }
        subscription_count = Subscription.objects.all().count()
        url = reverse('billing:subscription_create', kwargs={'version': 'v2'})
        client.force_login(user)
        client.post(url, data=data)
        subscription = Subscription.objects.all().first()

        assert Subscription.objects.all().count() == subscription_count + 1
        assert subscription.price == data['price']
        assert subscription.worker_count == data['worker_count']
        assert subscription.type == data['type']


class TestSubscriptionListView:
    @mock.patch.object(Subscription, 'deactivate')
    def test_get(self, mocked_method, client, user, company, relationship):
        plan1 = Subscription.objects.create(
            company=company,
            name='plan 1',
            type='monthly',
            price=500,
            worker_count=100,
        )
        plan2 = Subscription.objects.create(
            company=company,
            name='plan 2',
            type='monthly',
            price=1000,
            worker_count=200,
        )

        url = reverse('billing:subscription_list', kwargs={'version': 'v2'})
        client.force_login(user)
        response = client.get(url).json()

        assert len(response['subscriptions']) == 2
        assert plan1.id in (response['subscriptions'][0]['id'], response['subscriptions'][1]['id'])
        assert plan2.id in (response['subscriptions'][0]['id'], response['subscriptions'][1]['id'])
        assert Subscription.objects.get(id=plan2.id).active
        assert not Subscription.objects.get(id=plan1.id).active


class TestSubscriptionStatusView:
    def test_subscription_status_active(self, client, user, company, relationship):
        subscription = Subscription.objects.create(
            company=company,
            name='subscription',
            type='monthly',
            price=1000,
            worker_count=200,
            status='active'
        )

        url = reverse('billing:subscription_status', kwargs={'version': 'v2'})
        client.force_login(user)
        response = client.get(url).json()

        assert response['status'] == subscription.status

    def test_subscription_status_fail(self, client, user, company, relationship):
        url = reverse('billing:subscription_status', kwargs={'version': 'v2'})
        client.force_login(user)
        response = client.get(url).json()

        assert response['status'] == 'not_created'


class TestStripeCustomerCreateView:
    def test_get(self, client, user, company, relationship):
        url = reverse('billing:stripe_customer_create', kwargs={'version': 'v2'})
        client.force_login(user)
        client.post(url)

        assert not company.stripe_customer
        assert Company.objects.get(id=company.id).stripe_customer


class TestPaymentListView:
    def test_get(self, client, user, company, relationship, payment):
        url = reverse('billing:payment_list', kwargs={'version': 'v2'})
        client.force_login(user)
        response = client.get(url).json()

        assert len(response['payments']) == 1
        assert response['payments'][0]['amount'] == 100


class TestCheckPaymentInformationView:
    def test_get_success(self, client, user, company, relationship, payment):
        company.stripe_customer = 'randomstripeid'
        company.save()
        url = reverse('billing:check_payment_information', kwargs={'version': 'v2'})
        client.force_login(user)
        response = client.get(url).json()

        assert response['payment_information_submited']

    def test_get_fail(self, client, user, company, relationship, payment):
        url = reverse('billing:check_payment_information', kwargs={'version': 'v2'})
        client.force_login(user)
        response = client.get(url).json()

        assert not response['payment_information_submited']


class TestSubscriptionCancelView:
    @mock.patch.object(Subscription, 'deactivate')
    def test_get(self, mocked_method, client, user, company, relationship, subscription):
        url = reverse('billing:subscription_cancel', kwargs={'version': 'v2'})
        client.force_login(user)
        client.get(url)

        assert mocked_method.called
        assert not Subscription.objects.get(id=subscription.id).active


class TestCompanyListView:
    def test_get(self, client, user, company, subscription, payment):
        url = reverse('billing:company_list', kwargs={'version': 'v2'})
        client.force_login(user)
        response = client.get(url).json()

        assert response['count'] == 1
        assert bool(response['results'][0]['subscription']['last_time_billed'])
        assert response['results'][0]['sms_balance'] == 100


class TestDiscountView:
    def test_get(self, client, user, company, contact, manager, company_contact_rel):
        Discount.objects.create(
            company=company,
            payment_type='sms',
            percent_off=25,
            duration='once',
        )
        Discount.objects.create(
            company=company,
            payment_type='sms',
            percent_off=25,
            duration='once',
        )
        url = reverse('billing:discounts', kwargs={'version': 'v2'})
        client.force_login(user)
        response = client.get(url).json()

        assert response['count'] == 2

    def test_post(self, client, user, company):
        initial_discount_number = Discount.objects.count()
        data = {
            "company": {'id': str(company.id)},
            "payment_type": "sms",
            "percent_off": 25,
            "amount_off": None,
            "duration": "once",
            "duration_in_months": None,
        }
        url = reverse('billing:discounts', kwargs={'version': 'v2'})
        client.force_login(user)
        client.post(url, data=json.dumps(data), content_type='application/json')

        assert initial_discount_number + 1 == Discount.objects.count()
        assert Discount.objects.first().percent_off == data['percent_off']
