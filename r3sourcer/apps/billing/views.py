import stripe

from django.conf import settings
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from r3sourcer.apps.billing.models import Subscription
from r3sourcer.apps.billing.serializers import SubscriptionSerializer
from r3sourcer.apps.billing import STRIPE_INTERVALS


stripe.api_key = settings.STRIPE_SECRET_API_KEY


class SubscriptionCreateView(APIView):
    def post(self, *args, **kwargs):
        company = self.request.user.company
        plan_type = self.request.POST['type']
        worker_count = self.request.POST['worker_count']
        plan_name = 'R3sourcer {} plan for {} workers'.format(plan_type, worker_count)
        plan = stripe.Plan.create(
            product=settings.STRIPE_PRODUCT_ID,
            nickname=plan_name,
            interval=STRIPE_INTERVALS[plan_type],
            currency=company.currency,
            amount=self.request.POST['price'] * 100,
        )
        subscription = stripe.Subscription.create(
            customer=self.request.user.company.stripe_customer,
            items=[{"plan": plan.id}]
        )
        Subscription.objects.create(company=self.request.user.company,
                                    name=plan_name,
                                    type=plan_type,
                                    worker_count=worker_count,
                                    price=self.request.POST['price'],
                                    stripe_id=plan.id,
                                    subscription_id=subscription.id)
        return Response(status=status.HTTP_201_CREATED)


class SubscriptionListView(ListAPIView):
    def get(self, *args, **kwargs):
        subscriptions = Subscription.objects.filter(company=self.request.user.company)
        serializer = SubscriptionSerializer(subscriptions, many=True)
        data = {
            "subscriptions": serializer.data
        }
        return Response(data)


class StripeCustomerCreateView(APIView):
    def post(self, *args, **kwargs):
        company = self.request.user.company
        description = 'Customer for {} company'.format(company.name)
        customer = stripe.Customer.create(
            description=description,
            source=self.request.data.get('source'),
        )
        company.stripe_customer = customer.id
        company.save()
        return Response()


class SubscriptionStatusView(APIView):
    def get(self):
        company = self.request.user.company
        subscription = company.subscriptions.filter(active=True).first()
        data = {
            'status': subscription.status
        }
        return Response(data)
