import datetime

import stripe

from celery import shared_task
from django.conf import settings

from r3sourcer.apps.core.models import Company
from r3sourcer.apps.billing.models import Subscription, Payment


stripe.api_key = settings.STRIPE_SECRET_API_KEY


@shared_task
def charge_for_extra_workers(company):
    """
    Checks number of active workers. If that number is bigger that number of workers from client's plan
    then it charges extra fee for every worker.
    """
    today = datetime.datetime.today().date()
    company_list = Company.objects.filter(type=Company.COMPANY_TYPES.master) \
                                  .filter(subscriptions__active=True) \
                                  .filter(subscriptions__current_period_end=today)

    for company in company_list:
        subscription = company.active_subscription
        paid_workers = subscription.worker_count
        active_workers = company.active_workers(subscription.current_period_start)

        if active_workers > paid_workers:
            if subscription.type == Subscription.SUBSCRIPTION_TYPES.annual:
                extra_worker_fee = settings.ANNUAL_EXTRA_WORKER_FEE
            else:
                extra_worker_fee = settings.MONTHLY_EXTRA_WORKER_FEE

            amount = (active_workers - paid_workers) * extra_worker_fee
            charge = stripe.Charge.create(
                amount=amount * 100,
                currency=company.currency,
                customer=company.stripe_customer
            )
            Payment.objects.create(
                type=Payment.PAYMENT_TYPES.extra_workers,
                amount=amount,
                status=charge.status,
                stripe_id=charge.id
            )


@shared_task
def charge_for_sms(company_id, amount):
    company = Company.objects.get(id=id)
    charge = stripe.Charge.create(
        amount=amount * 100,
        currency='aud',
        customer=company.stripe_customer,
    )
    Payment.objects.create(
        type=Payment.PAYMENT_TYPES.sms,
        amount=amount,
        status=charge.status,
        stripe_id=charge.id
    )


@shared_task
def sync_subscriptions():
    for subscription in Subscription.objects.all():
        subscription.sync_status()
        subscription.sync_periods()
        subscription.save()
