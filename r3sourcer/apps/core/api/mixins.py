from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _
from django_filters import NumberFilter
from rest_framework import exceptions

from r3sourcer.apps.logger.main import endless_logger
from r3sourcer.apps.core.models import User, WorkflowObject
from r3sourcer.apps.core.utils.address import parse_google_address


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
            data['address'] = parse_google_address(address_data)
        except Exception as e:
            if self.raise_invalid_address:
                raise exceptions.ValidationError({'address': _('Please enter valid address!')})
            else:
                data['address'] = None

        return data['address'] if self.root_address else data
