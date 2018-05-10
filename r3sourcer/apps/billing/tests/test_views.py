from django.core.urlresolvers import reverse

from r3sourcer.apps.billing.models import Subscription
from r3sourcer.apps.core.models import Company


class TestSubscriptionCreateView:
    def test_post(self, client, user, company, relationship):
        company.stripe_customer = 'cus_CnGRCuSr6Fo0Uv'
        company.save()
        data = {
            "type": "monthly",
            "worker_count": 100,
            "price": 500
        }
        plan_count = Subscription.objects.all().count()
        url = reverse('billing:subscription_create')
        client.force_login(user)
        response = client.post(url, data=data)
        subscription = Subscription.objects.all().first()

        assert response.status_code == 201
        assert Subscription.objects.all().count() == plan_count + 1
        assert subscription.price == data['price']
        assert subscription.worker_count == data['worker_count']
        assert subscription.type == data['type']


class TestSubscriptionListView:
    def test_get(self, client, user, company, relationship):
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

        url = reverse('billing:subscription_list')
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

        url = reverse('billing:subscription_status')
        client.force_login(user)
        response = client.get(url).json()

        assert response['status'] == subscription.status

    def test_subscription_status_fail(self, client, user, company, relationship):
        url = reverse('billing:subscription_status')
        client.force_login(user)
        response = client.get(url).json()

        assert response['status'] == 'not_created'


class TestStripeCustomerCreateView:
    def test_get(self, client, user, company, relationship):
        url = reverse('billing:stripe_customer_create')
        client.force_login(user)
        client.post(url).json()

        assert not company.stripe_customer
        assert Company.objects.get(id=company.id).stripe_customer
