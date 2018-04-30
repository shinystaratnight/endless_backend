from django.core.urlresolvers import reverse

from r3sourcer.apps.billing.models import Plan


class TestPlanCreateView:
    def test_post(self, client, user, company, relationship):
        data = {
            "type": "monthly",
            "worker_count": 100,
            "price": 500
        }
        plan_count = Plan.objects.all().count()
        url = reverse('billing:plan_create')  # TODO: update it after you get rid of test page in billing app
        client.force_login(user)
        response = client.post(url, data=data)
        plan = Plan.objects.all().first()

        assert response.status_code == 201
        assert Plan.objects.all().count() == plan_count + 1
        assert plan.price == data['price']
        assert plan.worker_count == data['worker_count']
        assert plan.type == data['type']


class TestPlanListView:
    def test_get(self, client, user, company, relationship):
        plan1 = Plan.objects.create(
            company=company,
            name='plan 1',
            type='monthly',
            price=500,
            worker_count=100,
        )
        plan2 = Plan.objects.create(
            company=company,
            name='plan 2',
            type='monthly',
            price=1000,
            worker_count=200,
        )

        url = reverse('billing:plan_list')  # TODO: update it after you get rid of test page in billing app
        client.force_login(user)
        response = client.get(url).json()

        assert len(response['plans']) == 2
        assert plan1.id in (response['plans'][0]['id'], response['plans'][1]['id'])
        assert plan2.id in (response['plans'][0]['id'], response['plans'][1]['id'])
        assert Plan.objects.get(id=plan2.id).active
        assert not Plan.objects.get(id=plan1.id).active
