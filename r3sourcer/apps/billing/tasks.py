import stripe

from celery import shared_task
from django.conf import settings

from r3sourcer.apps.core.models import Company
from r3sourcer.apps.billing.models import Plan


stripe.api_key = settings.STRIPE_SECRET_API_KEY


def charge_for_extra_workers(company):
    """
    Checks number of active workers. If that number is bigger that number of workers from client's plan
    then it charges extra fee for every worker.
    """
    pass


# TODO: twilio feature has to be reworked first
@shared_task
def charge_for_sms(company_id, amount):
    """
    Calculates number of sms client sent and charges for them.
    """
    company = Company.objects.get(id=id)


@shared_task
def charge_companies():
    for company in Company.objects.filter(type=Company.COMPANY_TYPES.master):
        charge_for_extra_workers(company)


@shared_task
def sync_subscription_statuses():
    for subscription in Plan.objects.all():
        subscription.sync_status()
