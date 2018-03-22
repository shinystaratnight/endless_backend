import mock
import pytest

from django_filters import ChoiceFilter, CharFilter
from django_filters.rest_framework import FilterSet

from r3sourcer.apps.core_adapter.factories import _get_field, filter_factory
from r3sourcer.apps.core_adapter.filters import DateRangeFilter, DateTimeRangeFilter


class TestFunctions:

    def test_get_field(self):
        fields = [{'key': 'test'}]

        res = _get_field(fields, 'test')

        assert res == fields[0]

    def test_get_field_not_fount(self):
        fields = [{'key': 'test1'}]

        res = _get_field(fields, 'test')

        assert res is None

    def test_get_field_enpty(self):
        fields = []

        res = _get_field(fields, 'test')

        assert res is None


class FilterTest(FilterSet):
    field = CharFilter()

    class Meta:
        fields = ('field', )


class TestFilterFactory:

    def get_endpoint(self, spec=None):
        kwargs = {}
        if spec:
            kwargs['spec'] = spec
        endpoint = mock.Mock(**kwargs)
        endpoint.get_list_filter.return_value = ('field', )
        endpoint.model.__name__ = 'name'
        endpoint.get_metadata_fields.return_value = [{
            'key': 'field',
            'type': 'related',
        }]

        return endpoint

    @pytest.fixture
    def endpoint(self):
        return self.get_endpoint(['get_list_filter', 'model', 'get_metadata_fields'])

    def test_filter_factory_related(self, endpoint):
        res_cls = filter_factory(endpoint)

        assert isinstance(res_cls.declared_filters['field'], CharFilter)

    def test_filter_factory_related_base_filter_class(self):
        endpoint = self.get_endpoint()
        type(endpoint).filter_class = mock.PropertyMock(return_value=FilterSet)

        res_cls = filter_factory(endpoint)

        assert isinstance(res_cls.declared_filters['field'], CharFilter)

    def test_filter_factory_related_base_filter_class_with_field(self):
        endpoint = self.get_endpoint()
        endpoint.get_list_filter.return_value = ('field', 'field1')
        endpoint.get_metadata_fields.return_value = [{
            'key': 'field',
            'type': 'select',
        }, {
            'key': 'field1',
            'type': 'related',
        }]
        type(endpoint).filter_class = mock.PropertyMock(
            return_value=FilterTest
        )

        res_cls = filter_factory(endpoint)

        assert isinstance(res_cls.declared_filters['field'], CharFilter)

    def test_filter_factory_related_base_filter_class_with_all_fields(self):
        endpoint = self.get_endpoint()
        type(endpoint).filter_class = mock.PropertyMock(
            return_value=FilterTest
        )

        res_cls = filter_factory(endpoint)

        assert isinstance(res_cls.declared_filters['field'], CharFilter)

    def test_filter_factory_related_no_filters(self, endpoint):
        endpoint.get_list_filter.return_value = []

        res_cls = filter_factory(endpoint)

        assert res_cls is None

    def test_filter_factory_select_base_meta_choices(self, endpoint):
        endpoint.get_metadata_fields.return_value = [{
            'key': 'field',
            'type': 'select',
            'choices': [{'value': 'val', 'label': 'label'}]
        }]

        res_cls = filter_factory(endpoint)

        assert isinstance(res_cls.declared_filters['field'], ChoiceFilter)

    def test_filter_factory_select_base_filter_choices(self, endpoint):
        endpoint.get_list_filter.return_value = ({
            'field': 'field',
            'choices': [{'value': 'val', 'label': 'label'}]
        }, )
        endpoint.get_metadata_fields.return_value = [{
            'key': 'field',
            'type': 'select'
        }]

        res_cls = filter_factory(endpoint)

        assert isinstance(res_cls.declared_filters['field'], ChoiceFilter)

    def test_filter_factory_select_base_filter_choices_call(self, endpoint):
        def fn():
            return [{'value': 'val', 'label': 'label'}]  # pragma: no cover

        endpoint.get_list_filter.return_value = ({
            'field': 'field',
            'choices': fn
        }, )
        endpoint.get_metadata_fields.return_value = [{
            'key': 'field',
            'type': 'select'
        }]

        res_cls = filter_factory(endpoint)

        assert isinstance(res_cls.declared_filters['field'], ChoiceFilter)

    def test_filter_factory_select_base_no_choices(self, endpoint):
        endpoint.get_list_filter.return_value = ({
            'field': 'field',
        }, )
        endpoint.get_metadata_fields.return_value = [{
            'key': 'field',
            'type': 'select',
        }]

        res_cls = filter_factory(endpoint)

        assert res_cls is None

    def test_filter_factory_date_base(self, endpoint):
        endpoint.get_metadata_fields.return_value = [{
            'key': 'field',
            'type': 'date'
        }]

        res_cls = filter_factory(endpoint)

        assert isinstance(res_cls.declared_filters['field'], DateRangeFilter)

    def test_filter_factory_datetime_base(self, endpoint):
        endpoint.get_metadata_fields.return_value = [{
            'key': 'field',
            'type': 'datetime'
        }]

        res_cls = filter_factory(endpoint)

        assert isinstance(res_cls.declared_filters['field'], DateTimeRangeFilter)

    def test_filter_factory_unsupported_base(self, endpoint):
        endpoint.get_metadata_fields.return_value = [{
            'key': 'field',
            'type': 'input'
        }]

        res_cls = filter_factory(endpoint)

        assert res_cls is None
