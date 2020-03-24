from functools import reduce
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from easy_thumbnails.alias import aliases
from easy_thumbnails.exceptions import InvalidImageFormatError
from easy_thumbnails.files import ThumbnailerImageFieldFile
from phonenumbers import parse, NumberParseException, is_valid_number, format_number, PhoneNumberFormat, PhoneNumber


def get_thumbnail_picture(picture, alias):
    if not isinstance(picture, ThumbnailerImageFieldFile):
        return
    try:
        return picture.get_thumbnail(aliases.get(alias)).url
    except InvalidImageFormatError:
        pass


def get_host(request):
    if 'jwt_origin' in request.session:
        host_parts = urlparse(request.session['jwt_origin'])
    else:
        host_parts = urlparse(request.META.get('HTTP_ORIGIN', request.get_host()))

    return host_parts.netloc or host_parts.path


def parse_phone_number(phone_number, kwargs=None):
    if kwargs is None:
        kwargs = {}
    try:
        parsed_phone_number = parse(phone_number)
    except NumberParseException:
        parsed_phone_number = PhoneNumber()
    return parsed_phone_number, kwargs


def process_phone_number_leading_zero(phone_number, kwargs=None):
    if kwargs is None:
        kwargs = {}

    if phone_number.startswith('0'):
        country_code = kwargs.get('country_code', settings.DEFAULT_PHONE_NUMBER_COUNTRY_CODE)
        return '+{}{}'.format(country_code, phone_number[1:]), kwargs
    return phone_number, kwargs


def process_phone_number_leading_plus(phone_number, kwargs=None):
    if kwargs is None:
        kwargs = {}
    if not phone_number.startswith('+'):
        return '+{}'.format(phone_number), kwargs
    return phone_number, kwargs


PHONE_NUMBER_VALIDATION_CHAIN = (
    process_phone_number_leading_zero,
    process_phone_number_leading_plus,
    parse_phone_number,
)


def normalize_phone_number(phone_number, kwargs=None):
    if kwargs is None:
        kwargs = {}
    __phone_number, _ = reduce(lambda r, f: f(*r),
                               PHONE_NUMBER_VALIDATION_CHAIN,
                               (phone_number, kwargs))

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


def is_valid_phone_number(phone_number, kwargs=None):
    if kwargs is None:
        kwargs = {}
    phone = normalize_phone_number(phone_number, kwargs)
    return validate_phone_number(phone)
