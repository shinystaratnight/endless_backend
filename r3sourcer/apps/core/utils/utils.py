from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from easy_thumbnails.alias import aliases
from phonenumbers import parse, NumberParseException, is_valid_number, format_number, PhoneNumberFormat


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


def normalize_phone_number(phone_number):
    if phone_number.startswith('0'):
        phone_number = '+61{}'.format(phone_number[1:])
    elif not phone_number.startswith('+'):
        phone_number = '+{}'.format(phone_number)

    try:
        _phone_number = format_number(parse(phone_number), PhoneNumberFormat.E164)
    except NumberParseException:
        _phone_number = None
    return _phone_number


def validate_phone_number(phone_number):
    try:
        parsed = parse(phone_number)
    except NumberParseException:
        return False
    return is_valid_number(parsed)


def is_valid_email(email):
    try:
        validate_email(email)
    except ValidationError:
        return False
    return True


def is_valid_phone_number(phone_number):
    phone = normalize_phone_number(phone_number)
    return validate_phone_number(phone)
