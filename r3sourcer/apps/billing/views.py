import stripe

from django.conf import settings
from django.shortcuts import render
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from r3sourcer.apps.billing.models import PaymentInformation, Plan
from r3sourcer.apps.billing.serializers import PlanSerializer
from r3sourcer.apps.billing import STRIPE_INTERVALS


stripe.api_key = settings.STRIPE_SECRET_API_KEY


#  temporary view to help debug stripe integration
def billing_index(request):
    ## one time payment
    # charge = stripe.Charge.create(
    #     amount=999,
    #     currency='usd',
    #     source='tok_visa',
    #     receipt_email='fedotkin.dmitry@gmail.com',
    # )

    # recurring payment
    # create a service you charge for
    #product = stripe.Product.create(
    #    name='R3sourcer',
    #    type='service',
    #)

    context = {}
    return render(request, 'billing/billing.html', context)


def billing_callback(request):
    context = {
        'request': request
    }
    PaymentInformation.objects.create(
        company=request.user.company,
        email=request.POST['stripeEmail'],
        token_type=request.POST['stripeTokenType'],
        token=request.POST['stripeToken'],
    )
    print(dir(request))

    return render(request, 'billing/callback.html', context)


class PlanCreateView(APIView):
    def post(self, *args, **kwargs):
        plan_type = self.request.POST['type']
        worker_count = self.request.POST['worker_count']
        plan_name = 'R3sourcer {} plan for {} workers'.format(plan_type, worker_count)
        plan = stripe.Plan.create(
            product=settings.STRIPE_PRODUCT_ID,
            nickname=plan_name,
            interval=STRIPE_INTERVALS[plan_type],
            currency='aud',
            amount=self.request.POST['price'] * 100,
        )
        subscription = stripe.Subscription.create(
            customer=self.request.user.company.stripe_customer,
            items=[{"plan": plan.id}]
        )
        Plan.objects.create(company=self.request.user.company,
                            name=plan_name,
                            type=plan_type,
                            worker_count=worker_count,
                            price=self.request.POST['price'],
                            stripe_id=plan.id,
                            subscription_id=subscription.id)
        return Response(status=status.HTTP_201_CREATED)


class PlanListView(ListAPIView):
    def get(self, *args, **kwargs):
        plans = Plan.objects.filter(company=self.request.user.company)
        serializer = PlanSerializer(plans, many=True)
        data = {
            "plans": serializer.data
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
