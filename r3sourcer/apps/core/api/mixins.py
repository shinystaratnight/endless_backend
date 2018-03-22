from django.conf import settings

from r3sourcer.apps.logger.main import endless_logger
from r3sourcer.apps.core.models import User


class WorkflowStatesColumnMixin():

    def get_method_fields(self):
        method_fields = list(super().get_method_fields())
        return method_fields + ['active_states']

    def get_active_states(self, obj):
        if not obj:
            return

        states = obj.get_active_states()

        return [
            state.state.name_after_activation or state.state.name_before_activation
            for state in states
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
