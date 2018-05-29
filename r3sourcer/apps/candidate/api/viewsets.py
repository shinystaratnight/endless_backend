from django.utils.translation import ugettext_lazy as _
from rest_framework import status, exceptions
from rest_framework.response import Response

from r3sourcer.apps.core_adapter import constants
from r3sourcer.apps.core_adapter.utils import api_reverse_lazy

from r3sourcer.apps.core.api.decorators import list_route, detail_route
from r3sourcer.apps.core.api.viewsets import BaseApiViewset
from r3sourcer.apps.core.models import Company, InvoiceRule

from . import serializers
from ..models import Subcontractor


class CandidateContactViewset(BaseApiViewset):

    @list_route(
        methods=['post'],
        serializer=serializers.CandidateContactRegisterSerializer,
        fieldsets=({
            'type': constants.CONTAINER_ROW,
            'fields': ('title', 'first_name', 'last_name')
        }, {
            'type': constants.CONTAINER_ROW,
            'fields': ('email', 'phone_mobile')
        }, {
            'type': constants.CONTAINER_ROW,
            'fields': ({
                'type': constants.FIELD_BUTTON,
                'action': 'register_company_contact',
                'label': _('Company')
            }, {
                'type': constants.FIELD_BUTTON,
                'action': 'register_candidate_contact',
                'label': _('Candidate')
            })
        }, {
            'type': constants.CONTAINER_ROW,
            'fields': ('birthday', 'candidate.tax_file_number')
        }, {
            'type': constants.CONTAINER_ROW,
            'fields': ('address.country', 'address.state', 'address.city')
        }, {
            'type': constants.CONTAINER_ROW,
            'fields': ('address.street_address', 'address.postal_code')
        }, {
            'type': constants.FIELD_PICTURE,
            'field': 'picture',
            'label': _('Picture'),
            'label_upload': _('Choose a file'),
            'label_photo': _('Take a photo'),
        }, {
            'type': 'related',
            'field': 'tags',
            'endpoint': api_reverse_lazy('core/tags'),
            'label': _(
                'Please select Tickets and Licenses you currently hold'
            ),
            'add': False,
            'edit': False,
            'delete': False,
            'many': True,
        }, {
            'type': 'related',
            'field': 'skills',
            'endpoint': api_reverse_lazy('skills/skills'),
            'label': _(
                'Please select your role(s) or trade(s)'
            ),
            'add': False,
            'edit': False,
            'delete': False,
            'many': True,
        }, {
            'field': 'agree',
            'type': constants.FIELD_CHECKBOX,
            'label': _(
                'I agree that the information provided above is correct and '
                'I take personal responsibility in case it is not.\n'
                'I also aknowledge that registering for a second/duplicate '
                'account for myself, when detected, is subject to a fire'
            )
        })
    )
    def register(self, request, *args, **kwargs):
        serializer = serializers.CandidateContactRegisterSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        serializer = serializers.CandidateContactSerializer(instance)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data,
                        status=status.HTTP_201_CREATED,
                        headers=headers)

    @detail_route(
        methods=['get'],
        fieldsets=(
            {
                'type': constants.CONTAINER_ROW,
                # TODO: needs front-end implementation
                'wrapper': True,
                'fields': ({
                    'type': constants.CONTAINER_COLUMN,
                    'fields': ({
                        # TODO: needs front-end implementation
                        'type': constants.CONTAINER_ROW,
                        # TODO: needs front-end implementation
                        'inline': True,
                        'fields': ('contact.picture', 'contact.__str__'),
                    }, {
                        'type': constants.CONTAINER_COLLAPSE,
                        'label': _('Residency'),
                        'fields': ('residency', 'visa_type', 'visa_expiry_date', 'nationality'),
                    }, ),
                }, {
                    'type': constants.CONTAINER_COLUMN,
                    'fields': ({
                        'type': constants.CONTAINER_COLLAPSE,
                        'label': _('Personal Traits'),
                        'fields': (
                            'contact.gender', 'weight', 'transportation_to_work', 'strength', 'language',
                            'candidate_scores.reliability', 'candidate_scores.loyalty',
                            'candidate_scores.recruitment_score', 'candidate_scores.client_feedback',
                        ),
                    }, ),
                })
            }, {
                'type': constants.FIELD_RELATED,
                'delete': False,
                'list': True,
                'many': True,
                'create': False,
                'edit': False,
                'collapsed': True,
                'label': _('Skills'),
                'field': 'candidate_skills',
            }, {
                'type': constants.FIELD_RELATED,
                'delete': False,
                'list': True,
                'many': True,
                'create': False,
                'edit': False,
                'collapsed': True,
                'label': _('Tags'),
                'field': 'tag_rels',
            }, {
                'type': constants.CONTAINER_COLLAPSE,
                'label': _('Contact Details'),
                'fields': (
                    'contact.email', 'contact.phone_mobile', 'contact.address.street_address',
                    'contact.address.postal_code', 'contact.address.city', 'contact.address.state',
                    'contact.address.country',
                ),
            }
        )
    )
    def profile(self, request, pk, *args, **kwargs):
        return self.retrieve(request, pk=pk, *args, **kwargs)


class SubcontractorViewset(BaseApiViewset):

    http_method_names = ['post', 'put', 'get', 'options']

    @list_route(
        methods=['post'],
        serializer=serializers.CandidateContactRegisterSerializer,
        fieldsets=({
            'type': constants.CONTAINER_ROW,
            'fields': ('title', 'first_name', 'last_name')
        }, {
            'type': constants.CONTAINER_ROW,
            'fields': ('email', 'phone_mobile')
        }, {
            'type': constants.CONTAINER_ROW,
            'fields': ({
                'type': constants.FIELD_BUTTON,
                'action': 'register_company_contact',
                'label': _('Company')
            }, {
                'type': constants.FIELD_BUTTON,
                'action': 'register_candidate_contact',
                'label': _('Candidate')
            })
        }, {
            'type': constants.CONTAINER_ROW,
            'fields': ('birthday', 'candidate.tax_file_number',
                       'company.business_id')
        }, {
            'type': constants.CONTAINER_ROW,
            'fields': ('address.country', 'address.state', 'address.city')
        }, {
            'type': constants.CONTAINER_ROW,
            'fields': ('address.street_address', 'address.postal_code')
        }, {
            'type': constants.FIELD_PICTURE,
            'field': 'picture',
            'label': _('Picture'),
            'label_upload': _('Choose a file'),
            'label_photo': _('Take a photo'),
        }, {
            'type': 'related',
            'field': 'tags',
            'endpoint': api_reverse_lazy('core/tags'),
            'label': _(
                'Please select Tickets and Licenses you currently hold'
            ),
            'add': False,
            'edit': False,
            'delete': False,
            'many': True,
        }, {
            'type': 'related',
            'field': 'skills',
            'endpoint': api_reverse_lazy('skills/skills'),
            'label': _(
                'Please select your role(s) or trade(s)'
            ),
            'add': False,
            'edit': False,
            'delete': False,
            'many': True,
        }, {
            'field': 'agree',
            'type': constants.FIELD_CHECKBOX,
            'label': _(
                'I agree that the information provided above is correct and '
                'I take personal responsibility in case it is not.\n'
                'I also aknowledge that registering for a second/duplicate '
                'account for myself, when detected, is subject to a fire'
            )
        }, {
            'field': 'is_subcontractor',
            'type': constants.FIELD_CHECKBOX,
            'label': _('Is Subcontractor'),
        })
    )
    def register(self, request, *args, **kwargs):
        serializer = serializers.CandidateContactRegisterSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        candidate = serializer.save()
        company = Company.objects.create(
            name=str(candidate),
            expense_account='6-1006'
        )

        instance = Subcontractor.objects.create(
            company=company,
            primary_contact=candidate
        )

        InvoiceRule.objects.create(company=company)

        serializer = serializers.SubcontractorSerializer(instance)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data,
                        status=status.HTTP_201_CREATED,
                        headers=headers)
