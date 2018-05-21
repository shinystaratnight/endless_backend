import mock
import pytest

from django_filters.rest_framework import DjangoFilterBackend
from drf_auto_endpoint.decorators import bulk_action
from rest_framework import serializers
from rest_framework.response import Response

from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.core.api.serializers import (
    ApiBaseModelSerializer, RELATED_DIRECT, RELATED_NONE
)
from r3sourcer.apps.core.api.viewsets import BaseApiViewset
from r3sourcer.apps.core.models import Company, User


class ApiTestEndpoint(ApiEndpoint):
    model = Company
    fieldsets = (
        'business_id', 'name'
    )


class UserTestViewset(BaseApiViewset):
    filter_backends = (DjangoFilterBackend, )
    filter_class = None


class UserAnotherTestViewset(BaseApiViewset):
    filter_backends = []
    filter_class = None


class UserEndpoint(ApiEndpoint):
    model = User
    base_viewset = UserTestViewset
    fields = ('groups', 'date_joined', )
    list_filter = ('date_joined', )

    @bulk_action(method='POST', text='text')
    def delete(self, request):
        return Response()  # pragma: no cover


class AnotherUserEndpoint(ApiEndpoint):
    model = User
    base_viewset = UserAnotherTestViewset
    fields = ('groups', 'date_joined', )
    list_filter = ('date_joined', )


class TestApiEndpoint:

    def get_serializer(self, meta_fields='__all__', is_api_base=True):
        parent = ApiBaseModelSerializer if is_api_base else serializers.ModelSerializer

        class ApiTestCompanySerializer(parent):
            class Meta:
                model = Company
                fields = meta_fields

        return ApiTestCompanySerializer

    def test_get_fieldsets(self):
        endpoint = ApiTestEndpoint()

        assert endpoint.get_fieldsets() == ('business_id', 'name')

    @mock.patch.object(ApiTestEndpoint, 'get_serializer')
    def test_get_metadata_fields_serializer_fields_explicit(
            self, mock_serializer):
        mock_serializer.return_value = self.get_serializer(('business_id', 'name'))

        endpoint = ApiTestEndpoint()
        res = endpoint.get_metadata_fields()

        assert len(res) == 3

    @mock.patch.object(ApiTestEndpoint, 'get_serializer')
    def test_get_metadata_fields_serializer_fields_explicit_all(
            self, mock_serializer):
        mock_serializer.return_value = self.get_serializer(is_api_base=False)

        endpoint = ApiTestEndpoint()
        res = endpoint.get_metadata_fields()

        assert len(res) > 2

    def test_get_metadata_fields_serializer_fields_implicit_all(self):
        endpoint = ApiTestEndpoint()
        res = endpoint.get_metadata_fields()

        assert len(res) > 2

    def test_get_metadata_fields_info(self):
        endpoint = ApiTestEndpoint()
        serializer = endpoint.get_serializer()
        res = endpoint._get_metadata_fields_info(('business_id', 'name'), [], serializer())

        assert len(res) == 2

    def test_get_metadata_fields_info_exclude_fields(self):
        endpoint = ApiTestEndpoint()
        serializer = endpoint.get_serializer()
        res = endpoint._get_metadata_fields_info(
            ('business_id', 'name', '__str__'), [], serializer()
        )

        assert len(res) == 3

    def test_get_metadata_fields_info_base_related_field(self):
        endpoint = ApiTestEndpoint()
        serializer = endpoint.get_serializer()
        res = endpoint._get_metadata_fields_info(
            ('business_id', 'name', 'bank_account'), [], serializer()
        )

        assert len(res) == 3
        assert res[2]['type'] == 'related'

    def test_get_metadata_fields_info_model_field(self, settings):
        settings.REST_FRAMEWORK['RELATED'] = RELATED_DIRECT

        endpoint = ApiTestEndpoint()
        serializer = endpoint.get_serializer()
        res = endpoint._get_metadata_fields_info(
            ('business_id', 'name', 'bank_account'), [], serializer()
        )

        assert [f for f in res if f['key'] == 'bank_account.bank_name']

        settings.REST_FRAMEWORK['RELATED'] = RELATED_NONE

    # FIXME: fix this after refactor
    # def test_get_metadata_fields_info_many_to_many(self):
    #     class UserEndpoint(ApiEndpoint):
    #         model = User

    #     endpoint = UserEndpoint()
    #     serializer = endpoint.get_serializer()
    #     res = endpoint._get_metadata_fields_info(
    #         ('groups', 'date_joined'), [], serializer()
    #     )

    #     assert len(res) == 2
    #     assert res[0]['type'] == 'related'

    # def test_get_metadata_fields_info_method_fields(self):
    #     class Serializer(ApiBaseModelSerializer):
    #         method_fields = ('test', )

    #         class Meta:
    #             model = User
    #             fields = '__all__'

    #         def get_test(self, obj):
    #             return 'test'  # pragma: no cover

    #     class UserEndpoint(ApiEndpoint):
    #         model = User
    #         serializer = Serializer

    #     endpoint = UserEndpoint()
    #     serializer = endpoint.get_serializer()
    #     res = endpoint._get_metadata_fields_info(
    #         ('test', ), [], serializer()
    #     )

    #     assert len(res) == 1
    #     assert res[0]['type'] == 'static'

    def test_get_metadata_fields_list_name(self):
        class Serializer(ApiBaseModelSerializer):
            class Meta:
                model = Company
                fields = ('name', {
                    'manager': ('__str__', )
                })
                related = RELATED_DIRECT

        class CompanyEndpoint(ApiEndpoint):
            model = Company
            serializer = Serializer

        endpoint = CompanyEndpoint()
        serializer = endpoint.get_serializer()
        res = endpoint._get_metadata_fields_info(
            ('manager', 'name'), [], serializer(), meta=False
        )

        assert len(res) == 3
        assert res[0] == 'manager.__str__'
        assert res[1] == 'manager'
        assert res[2] == 'name'

    @mock.patch.object(ApiTestEndpoint, 'get_serializer')
    def test_get_metadata_fields_meta_false(self, mock_serializer):
        mock_serializer.return_value = self.get_serializer(('business_id', 'name'))

        endpoint = ApiTestEndpoint()
        res = endpoint.get_metadata_fields(meta=False)

        assert len(res) == 3

    def test_list_name_default(self):
        endpoint = ApiTestEndpoint()

        assert endpoint.get_list_name() == endpoint.singular_model_name

    def test_list_name_set(self):
        class Endpoint(ApiTestEndpoint):
            list_name = 'test'

        endpoint = Endpoint()

        assert endpoint.get_list_name() == 'test'

    def test_list_label_default(self):
        endpoint = ApiTestEndpoint()

        assert endpoint.get_list_label() == Company._meta.verbose_name

    def test_list_label_set(self):
        class Endpoint(ApiTestEndpoint):
            list_label = 'test'

        endpoint = Endpoint()

        assert endpoint.get_list_label() == 'test'

    def test_get_ordering_fields_default(self):
        class Endpoint(ApiTestEndpoint):
            pass

        with mock.patch.object(Endpoint, 'get_metadata_fields') as fields:
            fields.return_value = ['test']
            endpoint = Endpoint()

            assert list(endpoint.get_ordering_fields()) == ['test']

    def test_get_ordering_fields(self):
        class Endpoint(ApiTestEndpoint):
            ordering_fields = ['test']

        endpoint = Endpoint()

        assert list(endpoint.get_ordering_fields()) == ['test']

    def test_get_ordering_fields_with_mapping(self):
        class Endpoint(ApiTestEndpoint):
            ordering_fields = ['test']
            ordering_mapping = {'test': 'field'}

        endpoint = Endpoint()

        assert set(endpoint.get_ordering_fields()) == {'test', 'field'}

    def test_get_ordering_default(self):
        class Endpoint(ApiTestEndpoint):
            pass

        endpoint = Endpoint()

        assert len(endpoint.get_ordering()) == 0

    def test_get_ordering(self):
        class Endpoint(ApiTestEndpoint):
            ordering = ['test']

        endpoint = Endpoint()

        assert list(endpoint.get_ordering()) == ['test']

    def test_get_ordering_mapping_default(self):
        class Endpoint(ApiTestEndpoint):
            pass

        endpoint = Endpoint()

        assert endpoint.get_ordering_mapping() == {}

    def test_get_ordering_mapping(self):
        class Endpoint(ApiTestEndpoint):
            ordering_mapping = {'test': 'field'}

        endpoint = Endpoint()

        assert endpoint.get_ordering_mapping() == {'test': 'field'}

    def test_get_context_actions_default(self):
        class Endpoint(ApiTestEndpoint):
            pass

        endpoint = Endpoint()

        assert endpoint.get_context_actions() is None

    def test_get_context_actions(self):
        class Endpoint(ApiTestEndpoint):
            context_actions = [{
                'label': 'test',
                'endpoint': 'test',
            }]

        endpoint = Endpoint()

        assert len(endpoint.get_context_actions()) == 1

    def test_filter_class_with_django_backend(self):
        endpoint = UserEndpoint()

        assert DjangoFilterBackend in endpoint.get_viewset().filter_backends

    def test_filter_class_without_django_backend(self):
        endpoint = AnotherUserEndpoint()

        assert DjangoFilterBackend in endpoint.get_viewset().filter_backends

    @mock.patch('r3sourcer.apps.core.api.endpoints.api_reverse', return_value='/')
    def test_get_bulk_actions(self, mock_reverse):
        endpoint = UserEndpoint()

        res = endpoint.get_bulk_actions()

        assert len(res) == 1

    def test_get_list_tabs(self):
        class Endpoint(ApiTestEndpoint):
            list_tabs = ['test']

        endpoint = Endpoint()

        assert endpoint.get_list_tabs() == ['test']

    def test_get_list_tabs_empty(self):
        class Endpoint(ApiTestEndpoint):
            pass

        endpoint = Endpoint()

        assert endpoint.get_list_tabs() == []

    def test_get_list_buttons(self):
        class Endpoint(ApiTestEndpoint):
            list_buttons = ['test']

        endpoint = Endpoint()

        assert endpoint.get_list_buttons() == ['test']

    def test_get_list_buttons_empty(self):
        class Endpoint(ApiTestEndpoint):
            pass

        endpoint = Endpoint()

        assert endpoint.get_list_buttons() is None

    def test_get_list_editable_filter(self):
        class Endpoint(ApiTestEndpoint):
            list_editable_filter = ['test']

        endpoint = Endpoint()

        assert endpoint.get_list_editable_filter() == ['test']

    def test_get_list_editable_filter_empty(self):
        class Endpoint(ApiTestEndpoint):
            pass

        endpoint = Endpoint()

        assert endpoint.get_list_editable_filter() == []

    def test_get_fieldsets_add(self):
        class Endpoint(ApiTestEndpoint):
            fieldsets_add = ['test']

        endpoint = Endpoint()

        assert endpoint.get_fieldsets_add() == ['test']

    def test_get_fieldsets_add_empty(self):
        class Endpoint(ApiTestEndpoint):
            pass

        endpoint = Endpoint()

        assert endpoint.get_fieldsets_add() == ('business_id', 'name')
