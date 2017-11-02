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

        if metadata_type in (METADATA_LIST_TYPE, METADATA_FORMSET_TYPE):
            return AngularListApiAdapter(
                is_formset=metadata_type==METADATA_FORMSET_TYPE
            )
        return AngularApiAdapter(edit)
