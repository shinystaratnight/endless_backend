from functools import reduce
from urllib.parse import urlparse

import pytz
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from easy_thumbnails.alias import aliases
from phonenumbers import parse, NumberParseException, is_valid_number, format_number, PhoneNumberFormat, PhoneNumber
from pytz import UnknownTimeZoneError


def get_thumbnail_picture(picture, alias):
    if picture:
        try:
            return picture.get_thumbnail(aliases.get(alias)).url
        except Exception:
            pass


def get_host(request):
    if 'jwt_origin' in request.session:
        host_parts = urlparse(request.session['jwt_origin'])
    else:
        host_parts = urlparse(request.META.get('HTTP_ORIGIN', request.get_host()))

    return host_parts.netloc or host_parts.path


def parse_phone_number(phone_number):
    try:
        parsed_phone_number = parse(phone_number)
    except NumberParseException:
        parsed_phone_number = PhoneNumber()
    return parsed_phone_number


def process_phone_number_leading_zero(phone_number):
    if phone_number.startswith('0'):
        return '+61{}'.format(phone_number[1:])
    return phone_number


def process_phone_number_leading_plus(phone_number):
    if not phone_number.startswith('+'):
        return '+{}'.format(phone_number)
    return phone_number


PHONE_NUMBER_VALIDATION_CHAIN = (
    process_phone_number_leading_zero,
    process_phone_number_leading_plus,
    parse_phone_number,
)


def normalize_phone_number(phone_number):
    __phone_number = reduce(lambda r, f: f(r),
                            PHONE_NUMBER_VALIDATION_CHAIN,
                            phone_number)

    if is_valid_number(__phone_number) is False:
        return phone_number

    return format_number(__phone_number, PhoneNumberFormat.E164)


def validate_phone_number(phone_number):
    return is_valid_number(parse_phone_number(phone_number))


def is_valid_email(email):
    try:
        validate_email(email)
    except ValidationError:
        return False
    return True


def is_valid_phone_number(phone_number):
    phone = normalize_phone_number(phone_number)
    return validate_phone_number(phone)


def tz_time2utc_time(dt):
    """convert time with timezone to utc time
    :param dt: datetime.datetime with tz obj
    """
    return dt.astimezone(pytz.utc)


def local_time2utc_time(dt, timezone):
    """
    convert local time to utc
    :param dt: datetime.datetime obj
    :param timezone: string
    :return: datetime
    """
    local_tz = pytz.timezone(timezone)
    datetime_with_tz = local_tz.localize(dt, is_dst=None)
    return tz_time2utc_time(datetime_with_tz)


def geo_time_zone(lng, lat):
    tf = settings.TIME_ZONE_FINDER
    try:
        time_zone = tf.timezone_at(lng=lng, lat=lat)
    except UnknownTimeZoneError:
        time_zone = settings.TIME_ZONE
    return pytz.timezone(time_zone)


def utc2local(date_time, time_zone):
    return date_time.replace(tzinfo=pytz.utc).astimezone(time_zone)