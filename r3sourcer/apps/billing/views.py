import stripe

from datetime import datetime

from django.conf import settings
from rest_framework import status
from rest_framework.generics import ListAPIView, ListCreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from r3sourcer.apps.billing.models import Subscription, Payment, Discount
from r3sourcer.apps.billing.serializers import SubscriptionSerializer, PaymentSerializer, CompanySerializer, DiscountSerializer
from r3sourcer.apps.billing import STRIPE_INTERVALS
from r3sourcer.apps.core.models.core import Company, Contact


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
        current_period_start = None
        current_period_end = None

        if isinstance(subscription.current_period_start, int):
            current_period_start = datetime.fromtimestamp(subscription.current_period_start)
            current_period_end = datetime.fromtimestamp(subscription.current_period_end)

        sub = Subscription.objects.create(company=company,
                                          name=plan_name,
                                          type=plan_type,
                                          worker_count=worker_count,
                                          price=self.request.data.get('price', None),
                                          plan_id=plan.id,
                                          subscription_id=subscription.id,
                                          current_period_start=current_period_start,
                                          current_period_end=current_period_end)

        serializer = SubscriptionSerializer(sub)
        data = {
            "subscription": serializer.data
        }
        return Response(data, status=status.HTTP_201_CREATED)


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
        email = ''

        if company.billing_email:
            email = company.billing_email
        elif company.primary_contact:
            email = company.primary_contact.contact.email

        customer = stripe.Customer.create(
            description=description,
            source=self.request.data.get('source'),
            email=email
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


class CompanyListView(ListAPIView):
    queryset = Company.objects.filter(subscriptions__isnull=False)
    serializer_class = CompanySerializer


class DiscountView(ListCreateAPIView):
    queryset = Discount.objects.all()
    serializer_class = DiscountSerializer


class DisableSMSCompanyView(APIView):
    def get(self, *args, **kwargs):
        company = Company.objects.get(id=kwargs['id'])
        company.sms_enabled = False
        company.save()
        return Response()


class DisableSMSContactView(APIView):
    def get(self, *args, **kwargs):
        contact = Contact.objects.get(id=kwargs['id'])
        contact.sms_enabled = False
        contact.save()
        return Response()
