import stripe

from datetime import datetime

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import ListAPIView, ListCreateAPIView, GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from r3sourcer.apps.billing.models import Subscription, Payment, Discount, SMSBalance, SubscriptionType
from r3sourcer.apps.billing.serializers import SubscriptionSerializer, PaymentSerializer, \
    CompanySerializer, DiscountSerializer, SmsBalanceSerializer, SmsAutoChargeSerializer, SubscriptionTypeSerializer
from r3sourcer.apps.billing.tasks import charge_for_sms, fetch_payments
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
        sub_type = SubscriptionType.objects.get(type=plan_type)
        worker_count = self.request.data.get('worker_count', None)
        plan_name = 'R3sourcer {} plan for {} workers'.format(plan_type, worker_count)
        plan = stripe.Plan.create(
            product=settings.STRIPE_PRODUCT_ID,
            nickname=plan_name,
            interval=STRIPE_INTERVALS[plan_type],
            currency=company.currency,
            amount=round((int(self.request.data.get('price', None)) * 100) / 1.1),
        )

        subscription = stripe.Subscription.create(
            customer=company.stripe_customer,
            items=[{"plan": plan.id},],
            tax_percent=10.0,
        )
        current_period_start = None
        current_period_end = None

        if isinstance(subscription.current_period_start, int):
            # TODO change it to fromtimestamp if necessery 
            current_period_start = datetime.utcfromtimestamp(subscription.current_period_start)
            current_period_end = datetime.utcfromtimestamp(subscription.current_period_end)

        sub = Subscription.objects.create(company=company,
                                          name=plan_name,
                                          subscription_type=sub_type,
                                          worker_count=worker_count,
                                          price=self.request.data.get('price', None),
                                          plan_id=plan.id,
                                          subscription_id=subscription.id,
                                          current_period_start=current_period_start,
                                          current_period_end=current_period_end,
                                          status=subscription.status)
        serializer = SubscriptionSerializer(sub)
        customer = company.stripe_customer
        invoices = stripe.Invoice.list(customer=customer)['data']
        for invoice in invoices:
            if not Payment.objects.filter(stripe_id=invoice['id']).exists():
                Payment.objects.create(
                    company=company,
                    type=Payment.PAYMENT_TYPES.subscription,
                    amount=invoice['total'] / 100,
                    stripe_id=invoice['id'],
                    invoice_url=invoice['invoice_pdf'],
                    status=invoice['status']
                )
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
        description = '{}'.format(company.name)
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
        payments = Payment.objects.filter(company=self.request.user.company).order_by('-created')
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
        subscription.status = 'canceled'
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


class TwilioFundCreateView(APIView):
    def post(self, *args, **kwargs):
        company = self.request.user.company

        if not company.stripe_customer:
            data = {'error': 'User didnt provide payment information.'}
            return Response(status=status.HTTP_400_BAD_REQUEST, data=data)

        amount = self.request.data.get('amount')

        sms_balance, created = SMSBalance.objects.get_or_create(company=company)
        charge_for_sms.delay(company.id, amount, sms_balance.id)

        serializer = SmsBalanceSerializer(sms_balance)

        data = {
            "sms_balance": serializer.data
        }
        return Response(data, status=status.HTTP_201_CREATED)


class TwilioAutoChargeView(APIView):

    def get(self, *args, **kwargs):
        company = self.request.user.company
        sms_balance = SMSBalance.objects.get(company=company)
        serializer = SmsAutoChargeSerializer(sms_balance)
        data = {
            "sms_balance": serializer.data
            }
        return Response(data, status=status.HTTP_200_OK)

    def post(self, *args, **kwargs):
        company = self.request.user.company

        if not company.stripe_customer:
            data = {'error': 'User didnt provide payment information.'}
            return Response(status=status.HTTP_400_BAD_REQUEST, data=data)

        sms_balance = SMSBalance.objects.get(company=company)

        if 'top_up_amount' not in self.request.data or 'top_up_limit' not in self.request.data:
            data = {'error': 'Must provide top_up_amount and top_up_limit'}
            return Response(status=status.HTTP_400_BAD_REQUEST, data=data)

        sms_balance.top_up_amount = self.request.data.get('top_up_amount')
        sms_balance.top_up_limit = self.request.data.get('top_up_limit')
        sms_balance.auto_charge = self.request.data.get('auto_charge')
        sms_balance.save()

        serializer = SmsAutoChargeSerializer(sms_balance)

        data = {
            "sms_balance": serializer.data
            }
        return Response(data, status=status.HTTP_201_CREATED)


class SubscriptionTypeView(APIView):

    def get(self, *args, **kwargs):
        subscription_types = SubscriptionType.objects.all()
        serializer = SubscriptionTypeSerializer(subscription_types, many=True)
        data = {
            "subscription_types": serializer.data
            }
        return Response(data, status=status.HTTP_200_OK)
