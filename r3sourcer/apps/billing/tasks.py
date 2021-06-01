from datetime import timedelta
from decimal import Decimal

import stripe

from celery import shared_task
from celery.utils.log import get_task_logger

from django.conf import settings
from stripe.error import InvalidRequestError, CardError

from r3sourcer.apps.billing.models import (
                            Subscription,
                            Payment,
                            SMSBalance,
                            SubscriptionType,
                            StripeCountryAccount as sca,
    )
from r3sourcer.apps.core.models import Company, VAT
from r3sourcer.apps.email_interface.utils import get_email_service
from r3sourcer.apps.billing import STRIPE_INTERVALS
from r3sourcer.helpers.datetimes import utc_now

logger = get_task_logger(__name__)


@shared_task
def charge_for_extra_workers():
    """
    Checks number of active workers. If that number is bigger that number of workers from client's plan
    then it charges extra fee for every worker and adjust subscription plan to number of active workers.
    """
    today = utc_now().date()
    company_list = Company.objects.filter(type=Company.COMPANY_TYPES.master) \
                                  .filter(subscriptions__active=True) \
                                  .filter(subscriptions__current_period_end=today)

    for company in company_list:
        subscription = company.active_subscription
        paid_workers = subscription.worker_count
        active_workers = company.active_workers(subscription.current_period_start)
        country_code = company.get_country_code()
        stripe.api_key = sca.get_stripe_key(country_code)
        vat_object = VAT.get_vat(country_code)
        plan_type = subscription.subscription_type.type

        if active_workers > paid_workers:
            if plan_type == SubscriptionType.SUBSCRIPTION_TYPES.annual:
                extra_worker_fee = settings.ANNUAL_EXTRA_WORKER_FEE
            else:
                extra_worker_fee = settings.MONTHLY_EXTRA_WORKER_FEE

            extra_workers = active_workers - paid_workers
            amount = extra_workers * extra_worker_fee

            for discount in company.get_active_discounts('extra_workers'):
                amount = discount.apply_discount(amount)
            # charge for additional workers
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
            # adjust the monthly subscription plan to number of active workers
            if plan_type == SubscriptionType.SUBSCRIPTION_TYPES.monthly:
                amount = subscription.get_total_subscription_amount()
                if not subscription.price == amount:
                    plan_name = 'R3sourcer {} plan for {} workers'.format(plan_type, active_workers)
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
                                               proration_behavior='none',
                                               items=[{
                                                   'id': subscription_stripe['items']['data'][0].id,
                                                   'plan': plan.id,
                                               }]
                                               )
                    subscription.price = amount
                    subscription.save()


@shared_task
def charge_for_sms(company_id, amount, sms_balance_id):
    company = Company.objects.get(id=company_id)
    sms_balance = SMSBalance.objects.get(id=sms_balance_id)

    # try to create invoice and pay if last payment was successful
    if sms_balance.last_payment.status == Payment.PAYMENT_STATUSES.paid:
        country_code = company.get_hq_address().address.country.code2
        stripe_secret_key = sca.get_stripe_key(country_code)
        stripe.api_key = stripe_secret_key
        vat_object = VAT.get_vat(country_code).first()
        tax_percent = vat_object.stripe_rate

        for discount in company.get_active_discounts('sms'):
            amount = discount.apply_discount(amount)

        tax_value = tax_percent / 100 + 1
        stripe.InvoiceItem.create(customer=company.stripe_customer,
                                  amount=round(int(amount * 100 / tax_value)),
                                  currency=company.currency,
                                  description='Topping up sms balance')
        invoice = stripe.Invoice.create(customer=company.stripe_customer,
                                        default_tax_rates=[vat_object.stripe_id],
                                        description='Topping up sms balance')
        payment = Payment.objects.create(
            company=company,
            type=Payment.PAYMENT_TYPES.sms,
            amount=amount,
            stripe_id=invoice['id'],
            invoice_url=invoice['invoice_pdf'],
            status=invoice['status']
        )
        # pay an invoice after creation of corresponding Payment
        try:
            invoice.pay()
            # increase balance if payment is successful
            sms_balance.balance += Decimal(payment.amount)
        except CardError as ex:
            # mark as unpaid if error
            payment.status = Payment.PAYMENT_STATUSES.not_paid
            payment.save()
        finally:
            # in any case save the last payment to sms_balance
            sms_balance.last_payment = payment
            sms_balance.save()


@shared_task
def sync_subscriptions():
    # from contextlib import suppress
    # with suppress(InvalidRequestError):
    for subscription in Subscription.objects.filter(active=True):
        subscription.sync_status()
        subscription.update_permissions_on_status()
        subscription.sync_periods()
        subscription.save()
    for subscription in Subscription.objects.filter(active=False):
        subscription.sync_status()
        subscription.update_permissions_on_status()
        subscription.save()


@shared_task()
def fetch_payments():
    """creates invoices for not payed payments and downloads invoices from stripe for payed"""
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
        # check all customer invoices
        for invoice in invoices:
            # if subscription invoice is unpaid mark subscription as inactive
            if invoice['paid'] is False and invoice['subscription'] is not None:
                try:
                    sub = Subscription.objects.get(subscription_id=invoice['subscription'], active=True)
                    sub.active = False
                    sub.status = Subscription.SUBSCRIPTION_STATUSES.unpaid
                    sub.save()
                except Subscription.DoesNotExist:
                    pass

            # if payment is not created yet then create it for not-void invoices
            # void means this invoice was a mistake, and should be canceled.
            if invoice['status'] != 'void' and not Payment.objects.filter(stripe_id=invoice['id']).exists():
                payment_type = Payment.PAYMENT_TYPES.candidate
                if invoice['subscription'] is not None:
                    payment_type = Payment.PAYMENT_TYPES.subscription
                elif 'sms' in invoice['description']:
                    payment_type = Payment.PAYMENT_TYPES.sms
                elif 'extra workers' in invoice['description']:
                    payment_type = Payment.PAYMENT_TYPES.extra_workers
                Payment.objects.create(
                    company=company,
                    type=payment_type,
                    amount=invoice['total'] / 100,
                    stripe_id=invoice['id']
                )

        payments = Payment.objects.filter(invoice_url__isnull=True)
        for payment in payments:
            try:
                invoice = stripe.Invoice.retrieve(payment.stripe_id)
            except InvalidRequestError as ex:
                if ex.http_status == 404 and ex.code == 'resource_missing':
                    payment.delete()
                    continue

            if invoice['invoice_pdf']:
                payment.invoice_url = invoice['invoice_pdf']
                payment.save()

        not_paid_payments = Payment.objects.filter(status=Payment.PAYMENT_STATUSES.not_paid)
        for payment in not_paid_payments:
            try:
                invoice = stripe.Invoice.retrieve(payment.stripe_id)
            except InvalidRequestError as ex:
                if ex.http_status == 404 and ex.code == 'resource_missing':
                    payment.delete()
                    continue

            if invoice['paid']:
                payment.status = Payment.PAYMENT_STATUSES.paid
                payment.save()
                sms_balance = SMSBalance.objects.filter(last_payment=payment).first()

                if sms_balance:
                    sms_balance.balance += payment.amount
                    sms_balance.save()

            if invoice['status'] == 'void':
                payment.delete()


@shared_task
def send_sms_payment_reminder():
    balance_objects = SMSBalance.objects.filter(company__type='master',
                                                last_payment__status='not_paid')
    one_day_objects = balance_objects.filter(last_payment__created__gte=utc_now() - timedelta(days=1))
    two_days_objects = balance_objects.filter(last_payment__created__gte=utc_now() - timedelta(days=2)) \
                                      .filter(last_payment__created__lt=utc_now() - timedelta(days=1))
    email_interface = get_email_service()

    for sms_balance in one_day_objects:
        email_interface.send_tpl(sms_balance.company.primary_contact.contact,
                                 sms_balance.company,
                                 tpl_name='sms-payment-reminder-24')

    for sms_balance in two_days_objects:
        email_interface.send_tpl(sms_balance.company.primary_contact.contact,
                                 sms_balance.company,
                                 tpl_name='sms-payment-reminder-48')


@shared_task
def charge_for_new_amount():
    """"adjusts stripe plan to actual worker count"""
    company_list = Company.objects.filter(type=Company.COMPANY_TYPES.master) \
                                  .filter(subscriptions__active=True)

    for company in company_list:
        country_code = company.get_country_code()
        stripe.api_key = sca.get_stripe_key(country_code)
        subscription = company.active_subscription
        amount = subscription.get_total_subscription_amount()
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
                                       proration_behavior='none',
                                       items=[{
                                           'id': subscription_stripe['items']['data'][0].id,
                                           'plan': plan.id,
                                           }]
                                       )
            subscription.price = amount
            subscription.save()
        else:
            pass
