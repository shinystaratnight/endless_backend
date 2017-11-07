from celery import shared_task

from django.conf import settings
from django.utils import timezone


from .models import Country, CurrencyExchangeRates, PublicHoliday
from .open_exchange.client import client as openexchange_client
from .utils.public_holidays import EnricoApi, EnricoApiException


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

    for country in Country.objects.all():
        CurrencyExchangeRates.objects.update_or_create(
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
    country = Country.objects.get(code3=country_code)
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
        PublicHoliday.objects.get_or_create(country=country, name=data_item['englishName'], date=date)
