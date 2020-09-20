from datetime import timedelta
from decimal import Decimal

import stripe

from celery import shared_task
from celery.utils.log import get_task_logger

from django.conf import settings

from r3sourcer.apps.billing.models import (
                            Subscription,
                            Payment,
                            SMSBalance,
                            SubscriptionType,
                            StripeCountryAccount as sca,
    )
from r3sourcer.apps.core.models import Company, VAT
from r3sourcer.apps.email_interface.utils import get_email_service
from r3sourcer.helpers.datetimes import utc_now

logger = get_task_logger(__name__)


@shared_task
def charge_for_extra_workers():
    """
    Checks number of active workers. If that number is bigger that number of workers from client's plan
    then it charges extra fee for every worker.
    """
    today = utc_now().date()
    company_list = Company.objects.filter(type=Company.COMPANY_TYPES.master) \
                                  .filter(subscriptions__active=True) \
                                  .filter(subscriptions__current_period_end=today)

    for company in company_list:
        subscription = company.active_subscription
        paid_workers = subscription.worker_count
        active_workers = company.active_workers(subscription.current_period_start)
        country_code = 'EE'
        if company.get_hq_address():
            country_code = company.get_hq_address().address.country.code2
        stripe.api_key = sca.get_stripe_key(country_code)
        vat_object = VAT.objects.filter(country=country_code)

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
                                      amount=round((amount * 100) / 1.1),
                                      currency=company.currency,
                                      description='%s extra workers fee' % extra_workers)
            invoice = stripe.Invoice.create(customer=company.stripe_customer,
                                            default_tax_rates=[vat_object.stripe_id],
                                            description='%s extra workers fee' % extra_workers)
            Payment.objects.create(
                company=company,
                type=Payment.PAYMENT_TYPES.extra_workers,
                amount=amount,
                stripe_id=invoice['id'],
                invoice_url=invoice['invoice_pdf'],
                status=invoice['status']
                )


@shared_task
def charge_for_sms(company_id, amount, sms_balance_id):
    company = Company.objects.get(id=company_id)
    sms_balance = SMSBalance.objects.get(id=sms_balance_id)
    country_code = company.get_hq_address().address.country.code2
    stripe_secret_key = sca.get_stripe_key(country_code)
    stripe.api_key = stripe_secret_key
    vat_object = VAT.objects.get(country=country_code)
    tax_percent = vat_object.stripe_rate

    for discount in company.get_active_discounts('sms'):
        amount = discount.apply_discount(amount)

    tax_value = tax_percent / 100 + 1
    stripe.InvoiceItem.create(api_key=stripe_secret_key,
                              customer=company.stripe_customer,
                              amount=round(int(amount * 100 / tax_value)),
                              currency=company.currency,
                              description='Topping up sms balance')
    invoice = stripe.Invoice.create(api_key=stripe_secret_key,
                                    customer=company.stripe_customer,
                                    default_tax_rates=[vat_object.stripe_id],
                                    description='Topping up sms balance')
    invoice.pay()
    payment = Payment.objects.create(
        company=company,
        type=Payment.PAYMENT_TYPES.sms,
        amount=amount,
        stripe_id=invoice['id'],
        invoice_url=invoice['invoice_pdf'],
        status=invoice['status']
    )
    sms_balance.balance += Decimal(payment.amount)
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
        stripe.api_key = sca.get_stripe_key_on_company(company)
        if not company.stripe_customer:
            continue

        customer = company.stripe_customer
        try:
            invoices = stripe.Invoice.list(customer=customer)['data']
        except:
            continue

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
    balance_objects = SMSBalance.objects.filter(last_payment__status='not_paid')
    one_day_objects = balance_objects.filter(last_payment__created__gte=utc_now() - timedelta(days=1))
    two_days_objects = balance_objects.filter(last_payment__created__gte=utc_now() - timedelta(days=2)) \
                                      .filter(last_payment__created__lt=utc_now() - timedelta(days=1))
    email_interface = get_email_service()

    for sms_balance in one_day_objects:
        # TODO: propagate master company
        email_interface.send_tpl(sms_balance.company.primary_contact.contact.email, tpl_name='sms_payment_reminder_24')

    for sms_balance in two_days_objects:
        # TODO: propagate master company
        email_interface.send_tpl(sms_balance.company.primary_contact.contact.email, tpl_name='sms_payment_reminder_48')


@shared_task
def charge_for_new_amount():
    from r3sourcer.apps.billing import STRIPE_INTERVALS
    company_list = Company.objects.filter(type=Company.COMPANY_TYPES.master) \
                                  .filter(subscriptions__active=True)

    for company in company_list:
        country_code = 'EE'
        if company.get_hq_address():
            country_code = company.get_hq_address().address.country.code2
        stripe.api_key = sca.get_stripe_key(country_code)
        subscription = company.active_subscription
        active_workers = company.active_workers(subscription.current_period_start)
        # active_workers = subscription.worker_count
        if subscription.subscription_type.type == subscription.subscription_type.SUBSCRIPTION_TYPES.monthly:
            total_amount = subscription.subscription_type.start_range_price_monthly
        else:
            total_amount = subscription.subscription_type.start_range_price_annual
        start_workers = 5
        if active_workers > start_workers:
            total_amount += (active_workers - start_workers) * subscription.subscription_type.step_change_val
        if subscription.subscription_type.type == subscription.subscription_type.SUBSCRIPTION_TYPES.annual:
            if subscription.subscription_type.percentage_discount:
                total_amount = (total_amount * 12) - (total_amount * 12 / 100 * subscription.subscription_type.percentage_discount)
            else:
                total_amount = total_amount * 12 * .75
        if subscription.subscription_type.type == subscription.subscription_type.SUBSCRIPTION_TYPES.monthly:
            if subscription.subscription_type.percentage_discount:
                total_amount = total_amount - (
                total_amount / 100 * subscription.subscription_type.percentage_discount)
            else:
                total_amount = total_amount
        amount = total_amount
        if not subscription.price == amount:
            plan_type = subscription.subscription_type.type
            plan_name = 'R3sourcer {} plan for {} workers'.format(plan_type,
                                                                  subscription.worker_count)
            plan = stripe.Plan.create(
                product=settings.STRIPE_PRODUCT_ID,
                nickname=plan_name,
                interval=STRIPE_INTERVALS[plan_type],
                currency=company.currency,
                amount=round((int(amount) * 100) / 1.1),
                )
            subscription_stripe = stripe.Subscription.retrieve(subscription.subscription_id)
            stripe.Subscription.modify(subscription_stripe.id,
                                       cancel_at_period_end=False,
                                       items=[{
                                           'id': subscription_stripe['items']['data'][
                                               0].id,
                                           'plan': plan.id,
                                           }]
                                       )
            subscription.price = amount
            subscription.save()
        else:
            pass
