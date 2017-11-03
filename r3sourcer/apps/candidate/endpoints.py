from functools import partial

from django.utils.functional import lazy
from django.utils.translation import ugettext_lazy as _
from drf_auto_endpoint.decorators import bulk_action
from drf_auto_endpoint.router import router
from rest_framework.response import Response
from rest_framework.exceptions import ParseError

from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.core.models import WorkflowNode
from r3sourcer.apps.core_adapter import constants

from . import models
from .api import viewsets, serializers


class CandidateContactEndpoint(ApiEndpoint):

    model = models.CandidateContact
    base_viewset = viewsets.CandidateContactViewset
    serializer = serializers.CandidateContactSerializer

    fieldsets = (
        'contact',
        {
            'type': constants.CONTAINER_COLLAPSE,
            'name': _('Residency'),
            'collapsed': True,
            'fields': (
                'residency', 'nationality', 'visa_type', 'visa_expiry_date',
                'vevo_checked_at',
            ),
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'name': _('Formalities'),
            'collapsed': True,
            'fields': (
                'tax_file_number', 'referral', 'superannuation_fund',
                'super_member_number', 'bank_account',
                'emergency_contact_name', 'emergency_contact_phone',
                'employment_classification', 'autoreceives_sms',
            ),
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'name': _('Personal Traits'),
            'collapsed': True,
            'fields': (
                'weight', 'height', 'transportation_to_work', 'strength',
                'language', 'reliability_score', 'loyalty_score',
                'total_score',
            ),
        }, {
            'type': constants.FIELD_RELATED,
            'field': 'candidate_skills',
            'delete': True,
            'list': True,
            'label': _('Candidate Skills')
        }, {
            'type': constants.FIELD_RELATED,
            'field': 'tag_rels',
            'delete': True,
            'list': True,
            'label': _('Candidate Tags')
        }
    )

    list_display = (
        {
            'field': 'contact.picture',
            'type': constants.FIELD_PICTURE,
        },
        'contact', 'contact.is_available',
        {
            'label': _('Phone'),
            'fields': ({
                'type': constants.FIELD_LINK,
                'link': 'tel:{field}',
                'field': 'contact.phone_mobile',
            }, {
                'type': constants.FIELD_BUTTON,
                'action': 'sendSMS',
                'text': _('SMS'),
                'icon': 'fa-commenting',
                'fields': ('contact.phone_mobile',)
            }, {
                'type': constants.FIELD_LINK,
                'link': 'tel:{field}',
                'field': 'contact.address.phone_landline',
            }, {
                'type': constants.FIELD_LINK,
                'link': 'tel:{field}',
                'field': 'contact.address.phone_fax',
            },),
        }, {
            'field': 'contact.email',
            'link': 'mailto:{field}',
            'type': constants.FIELD_LINK,
            'label': _('E-mail'),
        }, 'contact.address.city', 'contact.address.state', 'contact.gender',
        'nationality', 'weight', 'height', 'transportation_to_work',
        'skill_list', 'tag_list', 'reliability_score', 'loyalty_score',
        'bmi', 'strength', 'language', 'total_score', 'state'
    )

    list_tabs = [{
        'label': _('Contacts'),
        'fields': (
            'phone', 'contact.email', 'contact.address.city',
            'contact.address.state',
        )
    }, {
        'label': _('Personal'),
        'fields': (
            'contact.gender', 'nationality', 'weight', 'height',
            'transportation_to_work',
        )
    }, {
        'label': _('Properties'),
        'fields': (
            'skill_list', 'tag_list', 'recruitment_agent'
        )
    }, {
        'label': _('Score'),
        'fields': (
            'reliability_score', 'loyalty_score', 'bmi', 'strength', 'language'
        )
    }]

    def get_list_filter(self):
        states_part = partial(
            WorkflowNode.get_model_all_states, models.CandidateContact
        )
        list_filter = [{
            'type': constants.FIELD_SELECT,
            'field': 'state',
            'choices': lazy(states_part, list)(),
        }, 'contact.gender', 'transportation_to_work', {
            'field': 'created_at',
            'type': constants.FIELD_DATE,
        }]

        return list_filter

    @bulk_action(method='POST', text=_('Send sms'), confirm=False, reload=False)
    def sendsms(self, request, *args, **kwargs):
        id_list = request.data

        if not id_list or not isinstance(id_list, list):
            raise ParseError(_('You should select Company addresses'))

        phone_numbers = set(self.model.objects.filter(
            id__in=id_list, contact__phone_mobile__isnull=False).values_list(
            'contact__phone_mobile', flat=True))

        return Response({
            'status': 'success',
            'phone_number': phone_numbers,
            'message': _('Phones numbers was selected'),
        })


class SkillRelEndpoint(ApiEndpoint):

    model = models.SkillRel
    serializer = serializers.SkillRelSerializer

    list_display = (
        'candidate_contact', 'skill', 'score', 'prior_experience'
    )

    list_editable = ('skill', 'score', 'prior_experience')


class TagRelEndpoint(ApiEndpoint):

    model = models.TagRel
    serializer = serializers.TagRelSerializer

    list_display = (
        'candidate_contact', 'tag', 'verified_by', 'verification_evidence'
    )

    list_editable = (
        'tag', 'verified_by',
        {
            'type': constants.FIELD_PICTURE,
            'field': 'verification_evidence',
            'label_upload': _('Choose a file'),
            'label_photo': _('Take a photo'),
        }
    )


class SubcontractorEndpoint(ApiEndpoint):

    model = models.Subcontractor
    base_viewset = viewsets.SubcontractorViewset
    serializer = serializers.SubcontractorSerializer


router.register(models.VisaType)
router.register(models.SuperannuationFund)
router.register(endpoint=CandidateContactEndpoint())
router.register(endpoint=SubcontractorEndpoint())
router.register(endpoint=TagRelEndpoint())
router.register(endpoint=SkillRelEndpoint())
router.register(models.SkillRateRel)
router.register(models.InterviewSchedule)
router.register(models.CandidateRel)
