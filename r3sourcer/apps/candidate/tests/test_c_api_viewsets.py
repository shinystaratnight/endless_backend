import json

import mock
import pytest

from rest_framework.test import force_authenticate

from r3sourcer.apps.candidate.endpoints import (
    CandidateContactEndpoint, SubcontractorEndpoint
)
from r3sourcer.apps.candidate.models import CandidateContact, Subcontractor


class ResourceMixin:
    endpoint_class = None
    actions = {
        'get': 'retrieve',
        'put': 'update',
        'post': 'create',
        'delete': 'destroy',
    }

    def get_response_as_view(self, request, endpoint=None, actions=None):
        kwargs = {
            'request': request,
            'partial': request.method.lower() == 'put'
        }
        endpoint = endpoint or self.endpoint_class
        viewset = endpoint().get_viewset()
        view = viewset.as_view(actions or self.actions)
        response = view(**kwargs)
        response.render()
        return response


@pytest.mark.django_db
class TestCompanyContactResource(ResourceMixin):
    endpoint_class = CandidateContactEndpoint
    actions = {
        'post': 'create',
    }

    @pytest.fixture
    def candidate_contact_data(self, country, skill, tag):
        candidate_contact_data = {
            'title': 'Mr.',
            'first_name': 'Test',
            'last_name': 'Tester',
            'email': 'tester@test.tt',
            'phone_mobile': '+12345678940',
            'address': {
                'street_address': 'test str',
                'country': str(country.id),
            },
            'skills': [str(skill.id)],
            'tags': [str(tag.id)],
            'agree': True,
        }
        return candidate_contact_data

    @mock.patch('r3sourcer.apps.core.models.core.fetch_geo_coord_by_address',
                return_value=(42, 42))
    def test_can_register_candidate_contact(self, mock_geo, rf, user, candidate_contact_data):
        req = rf.post('/api/v2/candidate_contacts/register/',
                      data=json.dumps(candidate_contact_data),
                      content_type='application/json')
        force_authenticate(req, user=user)

        response = self.get_response_as_view(req, actions={'post': 'register'})

        assert 'id' in response.data
        assert 201 == response.status_code
        assert CandidateContact.objects.filter(id=response.data['id']).exists()

    @mock.patch('r3sourcer.apps.core.models.core.fetch_geo_coord_by_address',
                return_value=(42, 42))
    def test_can_register_candidate_contact_do_not_agree(
            self, mock_geo, rf, user, candidate_contact_data):
        candidate_contact_data['agree'] = False
        req = rf.post('/api/v2/candidate_contacts/register/',
                      data=json.dumps(candidate_contact_data),
                      content_type='application/json')
        force_authenticate(req, user=user)

        response = self.get_response_as_view(req, actions={'post': 'register'})

        assert response.data['status'] == 'error'


@pytest.mark.django_db
class TestSubcontractorResource(ResourceMixin):
    endpoint_class = SubcontractorEndpoint
    actions = {
        'post': 'create',
    }

    @pytest.fixture
    def candidate_contact_data(self, country, skill, tag):
        candidate_contact_data = {
            'title': 'Mr.',
            'first_name': 'Test',
            'last_name': 'Tester',
            'email': 'tester@test.tt',
            'phone_mobile': '+12345678940',
            'address': {
                'street_address': 'test str',
                'country': str(country.id),
            },
            'skills': [str(skill.id)],
            'tags': [str(tag.id)],
            'agree': True,
        }
        return candidate_contact_data

    @mock.patch('r3sourcer.apps.core.models.core.fetch_geo_coord_by_address',
                return_value=(42, 42))
    def test_can_register_subcontractor(self, mock_geo, rf, user, candidate_contact_data):
        req = rf.post('/api/v2/candidate_contacts/register/',
                      data=json.dumps(candidate_contact_data),
                      content_type='application/json')
        force_authenticate(req, user=user)

        response = self.get_response_as_view(req, actions={'post': 'register'})

        assert 'id' in response.data
        assert 201 == response.status_code
        assert Subcontractor.objects.filter(id=response.data['id']).exists()

    @mock.patch('r3sourcer.apps.core.models.core.fetch_geo_coord_by_address',
                return_value=(42, 42))
    def test_can_register_subcontractor_do_not_agree(self, mock_geo, rf, user, candidate_contact_data):
        candidate_contact_data['agree'] = False
        req = rf.post('/api/v2/candidate_contacts/register/',
                      data=json.dumps(candidate_contact_data),
                      content_type='application/json')
        force_authenticate(req, user=user)

        response = self.get_response_as_view(req, actions={'post': 'register'})

        assert response.data['status'] == 'error'
