from datetime import datetime, timedelta

import pytz
from django.conf import settings


def utc_now():
    return datetime.now(pytz.utc)


def utc_yesterday():
    return utc_now() - timedelta(days=1)


def utc_tomorrow():
    return utc_now() + timedelta(days=1)


def datetime2timezone(date_time, time_zone):
    naive_dt = date_time.replace(tzinfo=None)
    return time_zone.localize(naive_dt, is_dst=None)


def tz2utc(dt):
    """convert time with timezone to utc time
    :param dt: datetime.datetime with tz obj
    """
    if dt is not None:
        return dt.astimezone(pytz.utc)


def utc2local(dt, tz):
    return dt.replace(tzinfo=pytz.utc).astimezone(tz)


def local2utc(dt, timezone):
    """
    Deprecated
    convert local time to utc
    :param dt: datetime.datetime obj
    :param timezone: string
    :return: datetime
    """
    local_tz = pytz.timezone(timezone)
    datetime_with_tz = local_tz.localize(dt, is_dst=None)
    return tz2utc(datetime_with_tz)


def geo_time_zone(lng, lat):
    if None in (lng, lat):
        return pytz.timezone('utc')

    tf = settings.TIME_ZONE_FINDER
    try:
        time_zone = tf.timezone_at(lng=lng, lat=lat)
    except pytz.UnknownTimeZoneError:
        time_zone = settings.TIME_ZONE
    return pytz.timezone(time_zone)
