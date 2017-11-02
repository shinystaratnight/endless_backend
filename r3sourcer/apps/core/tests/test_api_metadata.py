from rest_framework.request import Request

from r3sourcer.apps.core.api.metadata import ApiMetadata
from r3sourcer.apps.core_adapter.adapters import (
    AngularListApiAdapter, AngularApiAdapter
)


class TestApiMetadata:

    def test_get_default_metadata_adapter(self, rf):
        request = Request(rf.options('/'))
        metadata = ApiMetadata()

        adapter = metadata.get_adapter(request, None)

        assert isinstance(adapter, AngularListApiAdapter)

    def test_get_list_metadata_adapter(self, rf):
        request = Request(rf.options('/'))
        metadata = ApiMetadata()

        adapter = metadata.get_adapter(request, None)

        assert isinstance(adapter, AngularListApiAdapter)

    def test_get_form_metadata_adapter(self, rf):
        request = Request(rf.options('/?type=form'))
        metadata = ApiMetadata()

        adapter = metadata.get_adapter(request, None)

        assert isinstance(adapter, AngularApiAdapter)
