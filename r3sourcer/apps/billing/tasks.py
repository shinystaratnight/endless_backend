import datetime

import stripe

from celery import shared_task
from celery.utils.log import get_task_logger

from django.conf import settings

from r3sourcer.apps.billing.models import Subscription, Payment, SMSBalance, SubscriptionType
from r3sourcer.apps.core.models import Company
from r3sourcer.apps.email_interface.utils import get_email_service


stripe.api_key = settings.STRIPE_SECRET_API_KEY
logger = get_task_logger(__name__)


@shared_task
def charge_for_extra_workers():
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
            if subscription.subscription_type.type == SubscriptionType.SUBSCRIPTION_TYPES.annual:
                extra_worker_fee = settings.ANNUAL_EXTRA_WORKER_FEE
            else:
                extra_worker_fee = settings.MONTHLY_EXTRA_WORKER_FEE

            extra_workers = active_workers - paid_workers
            amount = (extra_workers) * extra_worker_fee

            for discount in company.get_active_discounts('extra_workers'):
                amount = discount.apply_discount(amount)

            stripe.InvoiceItem.create(customer=company.stripe_customer,
                                      amount=amount * 100,
                                      currency=company.currency,
                                      description='%s extra workers fee' % extra_workers)
            invoice = stripe.Invoice.create(customer=company.stripe_customer)
            Payment.objects.create(
                company=company,
                type=Payment.PAYMENT_TYPES.extra_workers,
                amount=amount,
                stripe_id=invoice['id']
            )


@shared_task
def charge_for_sms(company_id, amount, sms_balance_id):
    company = Company.objects.get(id=company_id)
    sms_balance = SMSBalance.objects.get(id=sms_balance_id)

    for discount in company.get_active_discounts('sms'):
        amount = discount.apply_discount(amount)

    stripe.InvoiceItem.create(customer=company.stripe_customer,
                              amount=amount * 100,
                              currency=company.currency,
                              description='Topping up sms balance')
    invoice = stripe.Invoice.create(customer=company.stripe_customer)
    payment = Payment.objects.create(
        company=company,
        type=Payment.PAYMENT_TYPES.sms,
        amount=amount,
        stripe_id=invoice['id']
    )
    sms_balance.balance += payment.amount
    sms_balance.last_payment = payment
    sms_balance.save()


@shared_task
def sync_subscriptions():
    for subscription in Subscription.objects.filter(active=True):
        subscription.sync_status()
        subscription.sync_periods()
        subscription.save()


@shared_task()
def fetch_payments():
    companies = Company.objects.all()

    for company in companies:
        if not company.stripe_customer:
            continue

        customer = company.stripe_customer
        invoices = stripe.Invoice.list(customer=customer)['data']
        payments = Payment.objects.filter(invoice_url__isnull=True)
        not_paid_payments = Payment.objects.filter(status=Payment.PAYMENT_STATUSES.not_paid)

        for invoice in invoices:
            if not Payment.objects.filter(stripe_id=invoice['id']).exists():
                Payment.objects.create(
                    company=company,
                    type=Payment.PAYMENT_TYPES.subscription,
                    amount=invoice['total'] / 100,
                    stripe_id=invoice['id']
                )

        for payment in payments:
            invoice = stripe.Invoice.retrieve(payment.stripe_id)

            if invoice['invoice_pdf']:
                payment.invoice_url = invoice['invoice_pdf']
                payment.save()

        for payment in not_paid_payments:
            invoice = stripe.Invoice.retrieve(payment.stripe_id)

            if invoice['paid']:
                payment.status = Payment.PAYMENT_STATUSES.paid
                payment.save()
                sms_balance = SMSBalance.objects.filter(last_payment=payment).first()

                if sms_balance:
                    sms_balance.balance += payment.amount
                    sms_balance.save()


@shared_task
def send_sms_payment_reminder():
    now = datetime.datetime.now()
    balance_objects = SMSBalance.objects.filter(last_payment__status='not_paid')
    one_day_objects = balance_objects.filter(last_payment__created__gte=now-datetime.timedelta(days=1))
    two_days_objects = balance_objects.filter(last_payment__created__gte=now-datetime.timedelta(days=2)) \
                                      .filter(last_payment__created__lt=now-datetime.timedelta(days=1))
    email_interface = get_email_service()

    for sms_balance in one_day_objects:
        email_interface.send_tpl(sms_balance.company.primary_contact.contact.email, tpl_name='sms_payment_reminder_24')

    for sms_balance in two_days_objects:
        email_interface.send_tpl(sms_balance.company.primary_contact.contact.email, tpl_name='sms_payment_reminder_48')


@shared_task
def charge_for_new_amount():
    today = datetime.datetime.today().date()
    company_list = Company.objects.filter(type=Company.COMPANY_TYPES.master) \
                                  .filter(subscriptions__active=True) \
                                  .filter(subscriptions__current_period_end=today)

    for company in company_list:
        subscription = company.active_subscription
        active_workers = company.active_workers(subscription.current_period_start)
        if subscription.subscription_type.amount > 6:
            amount = (active_workers) * subscription.subscription_type.amount
        else:
            amount = subscription.subscription_type.amount

        plan = stripe.Plan.retrieve(subscription.plan_id)
        plan.amount = amount * 100
        plan.save()
        subscription.price = amount
        subscription.save()
