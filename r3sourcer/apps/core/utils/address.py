from django.db.models import Q
from django.utils.text import slugify

from r3sourcer.apps.core.models import Country, Region, City


def get_address_parts(address_data):
    address_parts = {}

    for item in address_data.get('address_components', []):
        for item_type in item['types']:
            if item_type != 'political':
                address_parts[item_type] = item

    return address_parts


def get_street_address(address_parts):
    street_address = address_parts['route']['long_name']

    street_number = address_parts.get('street_number', {}).get('long_name')
    if street_number:
        street_address = ' '.join([street_number, street_address])

    return street_address


def parse_google_address(address_data):
    address_parts = get_address_parts(address_data)

    country = Country.objects.get(code2=address_parts['country']['short_name'])

    region_part = address_parts.get('administrative_area_level_1')
    try:
        region = region_part['long_name'].split(' ', 1)[0] if region_part['long_name'].split(' ', 1)[0] else region_part[
            'long_name']
        region = Region.objects.get(
            Q(name__icontains=region) | Q(alternate_names__contains=region_part['short_name']),
            country=country
        ) if region_part else None
    except Region.DoesNotExist:
        region = None

    city_part = address_parts.get('locality') or address_parts.get('sublocality')
    city_search = '%s%s' % (city_part['long_name'].replace(' ', ''), country.name.replace(' ', ''))
    if region:
        city = City.objects.filter(
            Q(search_names__icontains=city_search) | Q(name=city_part['long_name']),
            country=country, region=region,
        )
    else:
        city = City.objects.filter(
            Q(search_names__icontains=city_search), country=country,
        )
    if city.count() > 1:
        city = city.filter(
            Q(alternate_names__contains=city_part['long_name']) | Q(slug=slugify(city_part['long_name']))
        ).first()
    else:
        city = city.first()

    postal_code = address_parts.get('postal_code', {}).get('long_name')
    address = {
        'country': str(country.id),
        'state': str(region.id) if region else None,
        'city': str(city.id),
        'postal_code': postal_code,
        'street_address': get_street_address(address_parts),
    }

    location = address_data.get('geometry', {}).get('location')
    if location:
        address.update({
            'latitude': location.get('lat', 0),
            'longitude': location.get('lng', 0),
        })

    return address
