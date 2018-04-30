import stripe

from django.shortcuts import render
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from r3sourcer.apps.billing.models import PaymentInformation, Plan
from r3sourcer.apps.billing.serializers import PlanSerializer


#  temporary view to help debug stripe integration
def billing_index(request):
    public_key = "pk_test_d5AKTy7WjvRJBJ9wZduzAFjI"
    secret_key = "sk_test_y8pSRxUBV25cSB1pw80Hkd98"
    stripe.api_key = secret_key

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
        Plan.objects.create(company=self.request.user.company,
                            name='R3sourcer {} plan for {} workers'.format(plan_type, worker_count),
                            type=plan_type,
                            worker_count=worker_count,
                            price=self.request.POST['price'])
        return Response(status=status.HTTP_201_CREATED)


class PlanListView(ListAPIView):
    def get(self, *args, **kwargs):
        plans = Plan.objects.filter(company=self.request.user.company)
        serializer = PlanSerializer(plans, many=True)
        data = {
            "plans": serializer.data
        }
        return Response(data)
