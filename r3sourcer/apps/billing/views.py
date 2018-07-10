import stripe

from django.conf import settings
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from r3sourcer.apps.billing.models import Subscription, Payment
from r3sourcer.apps.billing.serializers import SubscriptionSerializer, PaymentSerializer
from r3sourcer.apps.billing import STRIPE_INTERVALS


stripe.api_key = settings.STRIPE_SECRET_API_KEY


class SubscriptionCreateView(APIView):
    def post(self, *args, **kwargs):
        company = self.request.user.company

        if not company.stripe_customer:
            data = {'error': 'User didnt provide payment information.'}
            return Response(status=status.HTTP_400_BAD_REQUEST, data=data)

        plan_type = self.request.data.get('type', None)
        worker_count = self.request.data.get('worker_count', None)
        plan_name = 'R3sourcer {} plan for {} workers'.format(plan_type, worker_count)
        plan = stripe.Plan.create(
            product=settings.STRIPE_PRODUCT_ID,
            nickname=plan_name,
            interval=STRIPE_INTERVALS[plan_type],
            currency=company.currency,
            amount=int(self.request.data.get('price', None)) * 100,
        )

        subscription = stripe.Subscription.create(
            customer=company.stripe_customer,
            items=[{"plan": plan.id}]
        )

        Subscription.objects.create(company=company,
                                    name=plan_name,
                                    type=plan_type,
                                    worker_count=worker_count,
                                    price=self.request.data.get('price', None),
                                    plan_id=plan.id,
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
        return Response(status=status.HTTP_201_CREATED)


class SubscriptionStatusView(APIView):
    def get(self, *args, **kwargs):
        status = 'not_created'
        company = self.request.user.company
        subscription = company.subscriptions.filter(active=True).first()

        if subscription:
            status = subscription.status

        data = {
            'status': status
        }
        return Response(data)


class PaymentListView(APIView):
    def get(self, *args, **kwargs):
        payments = Payment.objects.filter(company=self.request.user.company)
        serializer = PaymentSerializer(payments, many=True)
        data = {
            "payments": serializer.data,
        }
        return Response(data)


class CheckPaymentInformationView(APIView):
    def get(self, *args, **kwargs):
        return Response({
            "payment_information_submited": bool(self.request.user.company.stripe_customer)
        })


class SubscriptionCancelView(APIView):
    def get(self, *args, **kwargs):
        subscription = Subscription.objects.get(company=self.request.user.company, active=True)
        subscription.deactivate()
        subscription.active = False
        subscription.save()
        return Response()
