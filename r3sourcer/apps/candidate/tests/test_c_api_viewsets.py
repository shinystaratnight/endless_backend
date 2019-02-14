import json

import mock
import pytest

from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site

from rest_framework.test import force_authenticate

from r3sourcer.apps.candidate.endpoints import (
    CandidateContactEndpoint, SubcontractorEndpoint
)
from r3sourcer.apps.candidate.models import CandidateContact, Subcontractor, CandidateRel
from r3sourcer.apps.candidate.tests.utils import BaseTestCase, AnonymousUser
from r3sourcer.apps.core import models as core_models

class CandidateContactEndpointTest(CandidateContactEndpoint):

    permission_classes = []


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
    endpoint_class = CandidateContactEndpointTest
    actions = {
        'post': 'create',
    }

    @mock.patch('r3sourcer.apps.core.models.core.fetch_geo_coord_by_address', return_value=(42, 42))
    def test_can_register_candidate_contact(
        self, mock_geo, rf, user, staff_relationship, candidate_contact_data, site_company
    ):
        req = rf.post(
            '/candidate_contacts/register/', data=json.dumps(candidate_contact_data),
            content_type='application/json'
        )
        force_authenticate(req, user=user)

        response = self.get_response_as_view(req, actions={'post': 'register'})

        assert 201 == response.status_code
        assert 'id' in response.data
        assert CandidateContact.objects.filter(id=response.data['id']).exists()

    @mock.patch('r3sourcer.apps.core.models.core.fetch_geo_coord_by_address',
                return_value=(42, 42))
    def test_can_register_candidate_contact_do_not_agree(
            self, mock_geo, rf, user, candidate_contact_data):
        candidate_contact_data['agree'] = False
        req = rf.post('/candidate_contacts/register/',
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

    @mock.patch('r3sourcer.apps.core.models.core.fetch_geo_coord_by_address',
                return_value=(42, 42))
    def test_can_register_subcontractor(self, mock_geo, rf, user, candidate_contact_data):
        req = rf.post('/candidate_contacts/register/',
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
        req = rf.post('/candidate_contacts/register/',
                      data=json.dumps(candidate_contact_data),
                      content_type='application/json')
        force_authenticate(req, user=user)

        response = self.get_response_as_view(req, actions={'post': 'register'})

        assert response.data['status'] == 'error'

from django.contrib.contenttypes.models import ContentType

def workflow_state(candidate_id, company):
    content_type = ContentType.objects.get_for_model(CandidateContact)
    workflow, created = core_models.Workflow.objects.get_or_create(name="test_workflow", model=content_type)
    wf_node = core_models.WorkflowNode.objects.create(
        number=11, name_before_activation="State 11", workflow=workflow, rules={}, name_after_activation='Recruited - Available for Hire',
    )
    core_models.CompanyWorkflowNode.objects.get_or_create(company=company, workflow_node=wf_node)
    wf_obj = core_models.WorkflowObject.objects.create(
        object_id=candidate_id, state=wf_node)

    return wf_obj


class TestPoolAPITestCase(BaseTestCase):
    def get_url(self, view_name=None, args=None, kwargs=None):
        return '/candidate/candidatecontacts/pool/'

    def get_allowed_users(self):
        if self.request_user is not None:
            return [self.request_user]
        return [core_models.User.objects.create_superuser(
            email='test@test.tt', phone_mobile='+32345678901',
            password='test1234',
            )]

    def get_data(self):
        user = core_models.User.objects.create_user(
            email='test@test.vt', phone_mobile='+12345678801',
            password='test1234'
            )
        company = core_models.Company.objects.create(
            name='Company',
            business_id='123',
            type=core_models.Company.COMPANY_TYPES.master,
            )
        test_candidate = CandidateContact.objects.create(
            contact=user.contact, profile_price=13.0
            )
        company_contact = core_models.CompanyContact.objects.create(
            contact=user.contact
            )
        candidate_rel = CandidateRel.objects.create(
            candidate_contact=test_candidate,
            master_company=company,
            company_contact=company_contact,
            owner=True,
            active=True
            )
        workflow_state(candidate_id=str(test_candidate.id), company=company)
        return {'user': user, 'company': company, 'test_candidate': test_candidate,
                'company_contact': company_contact, 'candidate_rel': candidate_rel}

    def setUp(self):
        super().setUp()
        self.request_user = None

    def test_pool(self):
        data = self.get_data()
        resp = self.make_request()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['count'], 1)
        self.assertEqual(resp.data['results'][0]['id'], str(data['test_candidate'].id))

    def test_pool_anonym(self):
        self.request_user = AnonymousUser()
        data = self.get_data()
        resp = self.make_request()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['count'], 0)
        self.assertEqual(resp.data['results'], [])


class TestBuyAPITestCase(BaseTestCase):
    view_name = 'api:candidate/candidatecontacts-buy'

    def get_url(self, view_name=None, args=None, kwargs=None):
        return reverse(view_name or self.view_name,
                       kwargs=kwargs or self.get_view_kwargs())

    def get_allowed_users(self):
        if self.request_user is not None:
            return [self.request_user]
        return [core_models.User.objects.create_superuser(
            email='test@test.mm', phone_mobile='+32345678901',
            password='test1234'
            )]
    def get_data(self):
        user = core_models.User.objects.create_user(
            email='test@test.vt', phone_mobile='+12345678801',
            password='test1234'
            )
        company = core_models.Company.objects.create(
            name='Company',
            business_id='123',
            type=core_models.Company.COMPANY_TYPES.master,
            stripe_customer='cus_test'
            )
        test_candidate = CandidateContact.objects.create(
            contact=user.contact, profile_price=13.0
            )
        company_contact = core_models.CompanyContact.objects.create(
            contact=user.contact
            )
        candidate_rel = CandidateRel.objects.create(
            candidate_contact=test_candidate,
            master_company=company,
            company_contact=company_contact,
            owner=True,
            active=True
            )
        return {'user': user, 'company': company, 'test_candidate': test_candidate,
                'company_contact': company_contact, 'candidate_rel': candidate_rel}


    def setUp(self):
        super().setUp()
        self.request_user = None

    def test_buy_success(self):
        data = self.get_data()
        company_2 = core_models.Company.objects.create(
            name='Company2',
            business_id='1233',
            type=core_models.Company.COMPANY_TYPES.master,
            )
        data['candidate_rel'].master_company = company_2
        data['candidate_rel'].save()
        pk_ = str(data['test_candidate'].id)
        pk_company = str(data['company'].id)
        resp = self.make_request( method='POST', view_kwargs={"pk":pk_}, data={"company":pk_company})
        print("RESP", resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['status'], 'success')
        self.assertEqual(resp.data['message'], 'Please wait for payment to complete')

    def test_buy_cannot_sell_candidate(self):
        data = self.get_data()
        company_2 = core_models.Company.objects.create(
            name='Company2',
            business_id='1233',
            type=core_models.Company.COMPANY_TYPES.master,
            )
        data['candidate_rel'].master_company = company_2
        data['candidate_rel'].owner = False
        data['candidate_rel'].save()
        pk_ = str(data['test_candidate'].id)
        pk_company = str(data['company'].id)
        resp = self.make_request( method='POST', view_kwargs={"pk":pk_}, data={"company":pk_company})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['status'], 'error')
        self.assertIn('cannot sell this candidate.', resp.data['errors']['company'])

    def test_buy_cannot_find_company(self):
        data = self.get_data()
        pk_ = str(data['test_candidate'].id)
        resp = self.make_request( method='POST', view_kwargs={"pk":pk_})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['status'], 'error')
        self.assertIn('Cannot find company',
                      resp.data['errors']['company'])

    def test_buy_regular_company(self):
        data = self.get_data()
        data['company'].type = core_models.Company.COMPANY_TYPES.regular
        data['company'].save()
        pk_ = str(data['test_candidate'].id)
        pk_company = str(data['company'].id)
        resp = self.make_request(method='POST', view_kwargs={"pk": pk_},
                                 data={"company": pk_company})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['status'], 'error')
        self.assertIn("Only Master company can buy candidate's profile",
                      resp.data['errors']['company'])

    def test_buy_existing_rel(self):
        data = self.get_data()
        pk_ = str(data['test_candidate'].id)
        pk_company = str(data['company'].id)
        resp = self.make_request(method='POST', view_kwargs={"pk": pk_},
                                 data={"company": pk_company})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['status'], 'error')
        self.assertIn("Company already has this Candidate Contact",
                      resp.data['errors']['company'])

    def test_buy_stripe_customer_not_exist(self):
        data = self.get_data()
        data['company'].stripe_customer = None
        data['company'].save()
        company_2 = core_models.Company.objects.create(
            name='Company2',
            business_id='1233',
            type=core_models.Company.COMPANY_TYPES.master,
            )
        data['candidate_rel'].master_company = company_2
        data['candidate_rel'].save()
        pk_ = str(data['test_candidate'].id)
        pk_company = str(data['company'].id)
        resp = self.make_request(method='POST', view_kwargs={"pk":pk_}, data={"company":pk_company})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['status'], 'error')
        self.assertIn("Company has no billing information",
                      resp.data['errors']['company'])
