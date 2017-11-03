import pytest

from r3sourcer.apps.core.api.decorators import metadata, list_route, detail_route
from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.core.models import Company

from rest_framework.request import Request
from rest_framework.response import Response


class ApiTestEndpoint(ApiEndpoint):
    model = Company
    fieldsets = (
        'business_id', 'name'
    )


class AnotherApiTestEndpoint(ApiEndpoint):
    model = Company
    fieldsets = (
        'name'
    )


def method(self, request, *args, **kwargs):
    return Response(status=201)


class TestDecorators:

    @pytest.fixture
    def viewset(self):
        endpoint = ApiTestEndpoint()
        return endpoint.get_viewset()()

    def test_metadata(self, rf, viewset):
        req = rf.options('/')
        request = Request(req)

        resp = metadata(viewset, request)

        assert resp.status_code == 200

    def test_list_route(self, rf, viewset):
        req = rf.options('/')
        request = Request(req)

        meth = list_route()(method)

        resp = meth(viewset, request)

        assert resp.status_code == 200

    def test_list_route_explicit_options(self, rf, viewset):
        req = rf.options('/')
        request = Request(req)

        meth = list_route(methods=['get', 'options'])(method)

        resp = meth(viewset, request)

        assert resp.status_code == 200

    def test_list_route_not_options(self, rf, viewset):
        req = rf.get('/')
        request = Request(req)

        meth = list_route()(method)

        resp = meth(viewset, request)

        assert resp.status_code == 201

    def test_list_route_set_endpoint(self, rf, viewset):
        req = rf.options('/')
        request = Request(req)

        meth = list_route(endpoint=AnotherApiTestEndpoint())(method)

        resp = meth(viewset, request)

        assert resp.status_code == 200

    def test_detail_route(self, rf, viewset):
        req = rf.options('/')
        request = Request(req)

        meth = detail_route()(method)

        resp = meth(viewset, request)

        assert resp.status_code == 200

    def test_detail_route_explicit_options(self, rf, viewset):
        req = rf.options('/')
        request = Request(req)

        meth = detail_route(methods=['get', 'options'])(method)

        resp = meth(viewset, request)

        assert resp.status_code == 200

    def test_detail_route_not_options(self, rf, viewset):
        req = rf.get('/')
        request = Request(req)

        meth = detail_route()(method)

        resp = meth(viewset, request)

        assert resp.status_code == 201

    def test_detail_route_set_endpoint(self, rf, viewset):
        req = rf.options('/')
        request = Request(req)

        meth = detail_route(endpoint=AnotherApiTestEndpoint())(method)

        resp = meth(viewset, request)

        assert resp.status_code == 200
