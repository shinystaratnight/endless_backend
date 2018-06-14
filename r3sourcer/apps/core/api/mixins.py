from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from django_filters import NumberFilter
from rest_framework import exceptions

from r3sourcer.apps.logger.main import endless_logger
from r3sourcer.apps.core.models import User, WorkflowObject, Country, Region, City


class WorkflowStatesColumnMixin():

    def get_method_fields(self):
        method_fields = list(super().get_method_fields())
        return method_fields + ['active_states']

    def get_active_states(self, obj):
        if not obj:
            return

        states = obj.get_active_states()

        return [
            {
                '__str__': state.state.name_after_activation or state.state.name_before_activation,
                'number': state.state.number,
                'id': state.state.id,
            } for state in states
        ]


class CreatedUpdatedByMixin:

    def get_method_fields(self):
        method_fields = list(super().get_method_fields())
        return method_fields + ['created_by', 'updated_by']

    def _get_log_updated_by(self, obj, log_type=None):
        log_entry = endless_logger.get_recent_field_change(self.Meta.model, obj.id, 'id', log_type)
        if 'updated_by' in log_entry:
            user = User.objects.get(id=log_entry['updated_by'])
            email = user.email if hasattr(user, 'contact') else None
        else:
            email = None

        if not email:
            email = settings.SYSTEM_USER

        return email

    def get_created_by(self, obj):
        return self._get_log_updated_by(obj, 'create')

    def get_updated_by(self, obj):
        return self._get_log_updated_by(obj)


class ActiveStateFilterMixin:

    active_states = NumberFilter(method='filter_active_state')

    def _fetch_workflow_objects(self, value):  # pragma: no cover
        content_type = ContentType.objects.get_for_model(self.Meta.model)
        objects = WorkflowObject.objects.filter(
            state__number=value,
            state__workflow__model=content_type,
            active=True,
        ).distinct('object_id').values_list('object_id', flat=True)

        return objects

    def filter_active_state(self, queryset, name, value):
        objects = self._fetch_workflow_objects(value)
        return queryset.filter(id__in=objects)


class GoogleAddressMixin:

    raise_invalid_address = True
    root_address = False

    def prepare_related_data(self, data, is_create=False):
        data = super().prepare_related_data(data, is_create)

        if (not self.root_address and 'address' not in data) or (self.root_address and 'street_address' not in data):
            return data

        address_data = data['street_address'] if self.root_address else data['address']

        if not is_create and 'address_components' not in address_data:
            return data

        try:
            address_parts = {}

            for item in address_data['address_components']:
                for item_type in item['types']:
                    if item_type != 'political':
                        address_parts[item_type] = item

            country = Country.objects.get(code2=address_parts['country']['short_name'])

            region_part = address_parts.get('administrative_area_level_1')
            region = Region.objects.get(
                Q(name=region_part['long_name']) | Q(alternate_names__contains=region_part['short_name']),
                country=country
            ) if region_part else None

            city_part = address_parts.get('locality') or address_parts.get('sublocality')
            city_search = ' %s%s' % (city_part['long_name'].replace(' ', ''), country.name.replace(' ', ''))
            city = City.objects.filter(
                Q(search_names__icontains=city_search) | Q(name=city_part['long_name']),
                country=country, region=region,
            )
            if city.count() > 1:
                city = city.filter(
                    Q(alternate_names__contains=city_part['long_name']) | Q(slug=slugify(city_part['long_name']))
                ).first()
            else:
                city = city.first()

            postal_code = address_parts.get('postal_code', {}).get('long_name')
            street_address = address_parts['route']['long_name']

            street_number = address_parts.get('street_number', {}).get('long_name')
            if street_number:
                street_address = ' '.join([street_number, street_address])

            data['address'] = {
                'country': str(country.id),
                'state': str(region.id),
                'city': str(city.id),
                'postal_code': postal_code,
                'street_address': street_address,
            }

            location = address_data.get('geometry', {}).get('location')
            if location:
                data['address'].update({
                    'latitude': location.get('lat', 0),
                    'longitude': location.get('lng', 0),
                })

        except Exception as e:
            if self.raise_invalid_address:
                raise exceptions.ValidationError({'address': _('Please enter valid address!')})
            else:
                data['address'] = None

        return data['address'] if self.root_address else data
