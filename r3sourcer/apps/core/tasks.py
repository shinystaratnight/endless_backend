from contextlib import contextmanager

from celery import shared_task
from celery.five import monotonic

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from r3sourcer.celeryapp import app

from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.core.open_exchange.client import client as openexchange_client
from r3sourcer.apps.core.utils.public_holidays import EnricoApi, EnricoApiException


LOCK_EXPIRE = 5 * 60


@contextmanager
def memcache_lock(lock_id, oid):
    timeout_at = monotonic() + LOCK_EXPIRE - 3
    status = cache.add(lock_id, oid, LOCK_EXPIRE)
    try:
        yield status
    finally:
        if monotonic() < timeout_at:
            cache.delete(lock_id)


def one_sms_task_at_the_same_time(origin_task):
    lock_key_id_base = 'lock:task:{}:{}'.format(origin_task.__module__, origin_task.__name__)

    def wrap(self, *args, **kwargs):
        lock_key_id = '{}:{}'.format(lock_key_id_base, args[0]) if len(args) > 0 else lock_key_id_base

        with memcache_lock(lock_key_id, self.app.oid) as acquired:
            if acquired:
                origin_task(self, *args, **kwargs)

    wrap.__name__ = origin_task.__name__
    wrap.__module__ = origin_task.__module__
    return wrap


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
