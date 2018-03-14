from drf_auto_endpoint.metadata import AutoMetadata

from r3sourcer.apps.core_adapter.adapters import (
    AngularApiAdapter, AngularListApiAdapter
)
from r3sourcer.apps.core_adapter.constants import (
    METADATA_LIST_TYPE, METADATA_FORMSET_TYPE
)


class ApiMetadata(AutoMetadata):

    def get_adapter(self, request, view):
        metadata_type = request.query_params.get('type', METADATA_LIST_TYPE)
        edit = request.query_params.get('edit', True)
        editable_type = request.query_params.get('editable_type', 'default')
        fieldsets_type = request.query_params.get('fieldsets_type', 'default')

        if metadata_type in (METADATA_LIST_TYPE, METADATA_FORMSET_TYPE):
            return AngularListApiAdapter(
                is_formset=metadata_type == METADATA_FORMSET_TYPE,
                editable_type=editable_type
            )
        return AngularApiAdapter(edit, fieldsets_type=fieldsets_type)
