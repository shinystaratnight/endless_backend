import copy
import json

import mock
import pytest
from django.contrib.contenttypes.models import ContentType
from django.test.client import MULTIPART_CONTENT, BOUNDARY, encode_multipart

from drf_auto_endpoint.endpoints import Endpoint
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.test import force_authenticate

from r3sourcer.apps.activity.endpoints import (
    ActivityViewset,
    ActivityEndpoint
)
from r3sourcer.apps.core.service import FactoryService

from r3sourcer.apps.activity.models import Activity


class ResourceMixin:
    endpoint_class = None
    actions = {
        'get': 'retrieve',
        'put': 'update',
        'post': 'create',
        'delete': 'destroy',
    }

    def get_response_as_view(self, request, pk=None, endpoint=None, actions=None):
        kwargs = {'request': request, 'partial': request.method.lower() == 'put'}
        if pk is not None:
            kwargs['pk'] = pk
        endpoint = endpoint or self.endpoint_class
        viewset = endpoint().get_viewset()
        view = viewset.as_view(actions or self.actions)
        response = view(**kwargs)
        response.render()
        return response


@pytest.mark.django_db
class TestDashboardModules(ResourceMixin):
    endpoint_class = ActivityEndpoint
    actions = {
        'get': 'list',
        'post': 'create'
    }

    def test_get_activities(self, rf, primary_activity, secondary_activity):
        req = rf.get('/api/v2/endless-activity/activities/')
        force_authenticate(req, user=primary_activity.contact.user)

        resp_data = self.get_response_as_view(req)

        assert status.HTTP_200_OK == resp_data.status_code
        assert 'results' in resp_data.data
        assert len(resp_data.data['results']) == 1
        assert Activity.objects.all().count() == 2

    def test_get_activities_by_superuser(self, rf, primary_activity, secondary_activity):
        req = rf.get('/api/v2/endless-activity/activities/')

        primary_activity.contact.user.is_superuser = True

        force_authenticate(req, user=primary_activity.contact.user)

        resp_data = self.get_response_as_view(req)

        assert status.HTTP_200_OK == resp_data.status_code
        assert 'results' in resp_data.data
        assert len(resp_data.data['results']) == Activity.objects.all().count()
