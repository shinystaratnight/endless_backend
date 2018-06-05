from contextlib import contextmanager

from celery import shared_task
from celery.five import monotonic
from celery.utils.log import get_task_logger

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from r3sourcer.celeryapp import app

from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.core.open_exchange.client import client as openexchange_client
from r3sourcer.apps.core.utils import companies as core_companies_utils
from r3sourcer.apps.core.utils.public_holidays import EnricoApi, EnricoApiException
from r3sourcer.apps.email_interface.utils import get_email_service
from r3sourcer.apps.login.models import TokenLogin


LOCK_EXPIRE = 5 * 60


logger = get_task_logger(__name__)


@contextmanager
def memcache_lock(lock_id, oid):
    timeout_at = monotonic() + LOCK_EXPIRE - 3
    status = cache.add(lock_id, oid, LOCK_EXPIRE)
    try:
        yield status
    finally:
        if monotonic() < timeout_at:
            cache.delete(lock_id)


def one_task_at_the_same_time(id_lock=False):

    def decorator(origin_task):
        lock_key_id_base = 'lock:task:{}:{}'.format(origin_task.__module__, origin_task.__name__)

        def wrap(self, *args, **kwargs):
            lock_key_id = '{}:{}'.format(lock_key_id_base, args[0]) if len(args) > 0 and id_lock else lock_key_id_base

            with memcache_lock(lock_key_id, self.app.oid) as acquired:
                if acquired:
                    origin_task(self, *args, **kwargs)

        wrap.__name__ = origin_task.__name__
        wrap.__module__ = origin_task.__module__
        return wrap

    return decorator


@shared_task()
def fetch_coordinate_address(app_label, model_name, object_id, full_address):
    """
    Fetching coordinate address
    """

    from django.apps import apps

    model_class = apps.get_model(app_label, model_name)
    instance = model_class.objects.get(id=object_id)
    if instance.get_full_address() == full_address:
        instance.fetch_geo_coord()


@shared_task(bind=True)
def exchange_rates_sync(self):
    """
    Sync exchange rates from Open Exchange Rates service
    """
    rates = openexchange_client.latest()

    if not rates:
        return

    for country in core_models.Country.objects.all():
        core_models.CurrencyExchangeRates.objects.update_or_create(
            from_currency=settings.DEFAULT_CURRENCY,
            to_currency=country.currency,
            defaults={'exchange_rate': rates.get(country.currency, 1)}
        )


@shared_task()
def fetch_holiday_dates(country_code, year, month):
    """
    Fetching holiday dates from api

    :param country_code: str Country.code3
    :param year: int Year for fetching
    :param month: int Month for fetching
    :return:
    """
    country = core_models.Country.objects.get(code3=country_code)
    data_dict = {'country': country_code, 'year': year}
    if month:
        data_dict['month'] = month
    client = EnricoApi()

    if month:
        handler = client.fetch_for_month
    else:
        handler = client.fetch_for_year

    response = handler(**data_dict)
    if not isinstance(response, list):
        # raise exception for incorrect response
        raise EnricoApiException(response)

    for data_item in response:
        date = timezone.datetime(data_item['date']['year'], data_item['date']['month'], data_item['date']['day'])
        core_models.PublicHoliday.objects.get_or_create(
            country=country, name=data_item['englishName'], date=date)


one_sms_task_at_the_same_time = one_task_at_the_same_time(True)


@app.task(bind=True)
@one_sms_task_at_the_same_time
def send_trial_email(self, contact_id, auto_password):
    try:
        contact = core_models.Contact.objects.get(id=contact_id)
    except core_models.Contact.DoesNotExist as e:
        logger.error(e)
    else:
        try:
            email_interface = get_email_service()
        except ImportError:
            logger.exception('Cannot load SMS service')
            return

        site_url = core_companies_utils.get_site_url(user=contact.user)
        data_dict = {
            'contact': contact,
            'password': auto_password,
            'site_url': site_url,
        }

        email_interface.send_tpl(contact.email, tpl_name='trial-user-register', **data_dict)


@shared_task()
def cancel_trial(user_id):
    try:
        user = core_models.User.objects.get(id=user_id, role__name=core_models.Role.ROLE_NAMES.trial)
    except core_models.User.DoesNotExist:
        logger.exception('Cannot find trial user')
    else:
        user.user_permissions.exclude(codename__icontains='_get').delete()


@shared_task()
def terminate_company_contact(company_contact_rel_id):
    try:
        company_contact_rel = core_models.CompanyContactRelationship.objects.get(id=company_contact_rel_id)
    except core_models.CompanyContactRelationship.DoesNotExist:
        logger.exception('Cannot find company contact relation to terminate')
    else:
        termination_date = company_contact_rel.termination_date
        today = timezone.localtime(timezone.now()).date()

        if termination_date and termination_date == today:
            company_contact_rel.active = False
            company_contact_rel.save()
