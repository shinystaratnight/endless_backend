from functools import partial

from django.utils.functional import lazy
from django.utils.translation import ugettext_lazy as _

from drf_auto_endpoint.decorators import bulk_action
from drf_auto_endpoint.router import router
from rest_framework.response import Response
from rest_framework.exceptions import ParseError

from r3sourcer.apps.core_adapter import constants
from r3sourcer.apps.core.utils.text import format_lazy
from r3sourcer.apps.core_adapter.utils import api_reverse_lazy
from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.core.api import endpoints as core_endpoints
from r3sourcer.apps.candidate import models as candidate_models
from r3sourcer.apps.candidate.api import viewsets as candidate_viewsets
from r3sourcer.apps.candidate.api import serializers as candidate_serializers


class CandidateContactEndpoint(core_endpoints.ApiEndpoint):

    model = candidate_models.CandidateContact
    base_viewset = candidate_viewsets.CandidateContactViewset
    serializer = candidate_serializers.CandidateContactSerializer

    fieldsets = (
        {
            'type': constants.CONTAINER_ROW,
            'label': _('General'),
            'collapsed': False,
            'fields': (
                {
                    'type': constants.CONTAINER_COLUMN,
                    'fields': ({
                        'type': constants.FIELD_PICTURE,
                        'field': 'contact.picture',
                        'read_only': True,
                        'label': _('Photo'),
                        'file': False,
                        'photo': False,
                        'custom': [],
                    },)
                }, {
                    'type': constants.CONTAINER_COLUMN,
                    'fields': ({
                        'type': constants.FIELD_RELATED,
                        'field': 'contact',
                        'read_only': True,
                        'label': _('Contact'),
                        'custom': (
                            'contact.__str__', 'contact.address.__str__', 'contact.phone_mobile', 'contact.email'
                        ),
                    },)
                }, {
                    'type': constants.CONTAINER_COLUMN,
                    'fields': ({
                        'type': constants.FIELD_RELATED,
                        'field': 'recruitment_agent',
                        'read_only': True,
                        'label': _('Recruitment Agent'),
                        'custom': (
                            'recruitment_agent.job_title', 'recruitment_agent.contact.__str__',
                            'recruitment_agent.contact.phone_mobile'
                        ),
                    },)
                },
            )
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'name': _('Residency'),
            'collapsed': True,
            'fields': (
                'residency', {
                    'type': constants.FIELD_RELATED,
                    'field': 'visa_type',
                    'showIf': [
                        {
                            'residency': str(candidate_models.CandidateContact.RESIDENCY_STATUS_CHOICES.temporary),
                        }
                    ],
                }, {
                    'type': constants.FIELD_DATE,
                    'field': 'visa_expiry_date',
                    'showIf': [
                        'visa_type.id',
                    ],
                }, {
                    'type': constants.FIELD_DATE,
                    'field': 'vevo_checked_at',
                    'showIf': [
                        'visa_type.id',
                    ],
                }, 'nationality',
            ),
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'name': _('Formalities'),
            'collapsed': True,
            'fields': (
                'tax_file_number', 'superannuation_fund', {
                    'type': constants.FIELD_TEXT,
                    'field': 'super_member_number',
                    'showIf': [
                        'superannuation_fund.id'
                    ],
                }, 'bank_account', 'emergency_contact_name', 'emergency_contact_phone', 'employment_classification',
                'autoreceives_sms',
            ),
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'name': _('Personal Traits'),
            'collapsed': True,
            'fields': (
                {
                    'type': constants.FIELD_TEXT,
                    'field': 'height',
                },
                'weight', 'transportation_to_work', 'strength', 'language',
            ),
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'name': _('Candidate rating'),
            'collapsed': True,
            'fields': (
                {
                    'field': 'candidate_scores.id',
                    'type': constants.FIELD_TEXT,
                    'send': False,
                }, {
                    'field': 'candidate_scores.loyalty',
                    'type': constants.FIELD_STATIC,
                    'read_only': True,
                    'label': _('Loyalty Score'),
                    'send': False,
                }, {
                    'field': 'candidate_scores.reliability',
                    'type': constants.FIELD_STATIC,
                    'read_only': True,
                    'label': _('Reliability Score'),
                    'send': False,
                }, {
                    'field': 'candidate_scores.client_feedback',
                    'type': constants.FIELD_STATIC,
                    'read_only': True,
                    'label': _('Client Feedback'),
                    'send': False,
                }, {
                    'field': 'candidate_scores.recruitment_score',
                    'type': constants.FIELD_STATIC,
                    'read_only': True,
                    'label': _('Recruitment Score'),
                    'send': False,
                },
            ),
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'name': _('Messages'),
            'collapsed': True,
            'fields': (
                'message_by_sms', 'message_by_email',
            ),
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'name': _('Other'),
            'collapsed': True,
            'fields': (
                {
                    'field': 'created_at',
                    'type': constants.FIELD_DATE,
                    'read_only': True,
                    'label': _('Created at'),
                    'send': False,
                }, {
                    'field': 'updated_at',
                    'type': constants.FIELD_DATE,
                    'read_only': True,
                    'label': _('Updated at'),
                    'send': False,
                }
            ),
        }, {
            'type': constants.FIELD_RELATED,
            'delete': True,
            'list': True,
            'many': True,
            'create': True,
            'edit': True,
            'collapsed': True,
            'label': _('Notes'),
            'field': 'notes',
        }, {
            'type': constants.FIELD_LIST,
            'field': 'id_',
            'query': {
                'candidate_contact': '{id}',
            },
            'collapsed': True,
            'label': _('Skills'),
            'add_label': _('Add'),
            'endpoint': api_reverse_lazy('candidate/skillrels'),
            'prefilled': {
                'candidate_contact': '{id}',
            }
        }, {
            'type': constants.FIELD_RELATED,
            'delete': True,
            'list': True,
            'many': True,
            'create': True,
            'edit': True,
            'collapsed': True,
            'label': _('Candidate Tags'),
            'field': 'tag_rels',
        }, {
            'type': constants.FIELD_LIST,
            'field': 'id_',
            'query': {
                'contact': '{contact.id}',
            },
            'collapsed': True,
            'label': _('Activities'),
            'add_label': _('Add'),
            'endpoint': api_reverse_lazy('activity/activities'),
            'prefilled': {
                'contact': '{contact.id}',
            }
        }, {
            'type': constants.FIELD_TIMELINE,
            'label': _('States Timeline'),
            'field': 'id',
            'endpoint': format_lazy('{}timeline/', api_reverse_lazy('core/workflownodes')),
            'query': {
                'model': 'candidate.candidatecontact',
                'object_id': '{id}',
            },
        }, {
            'type': constants.FIELD_LIST,
            'query': {
                'object_id': '{id}'
            },
            'collapsed': True,
            'label': _('Candidate States History'),
            'add_label': _('Add'),
            'endpoint': api_reverse_lazy('core/workflowobjects'),
            'prefilled': {
                'object_id': '{id}',
            }
        }, {
            'query': {
                'contact': '{contact.id}',
            },
            'type': constants.FIELD_LIST,
            'collapsed': True,
            'label': _('Candidate Unavailabilities'),
            'endpoint': api_reverse_lazy('core/contactunavailabilities'),
        }, {
            'type': constants.FIELD_LIST,
            'query': {
                'candidate_contact': '{id}'
            },
            'collapsed': True,
            'label': _('Job Offers'),
            'endpoint': format_lazy('{}candidate/',  api_reverse_lazy('hr/joboffers')),
        }, {
            'query': {
                'candidate_contact': '{id}'
            },
            'type': constants.FIELD_LIST,
            'collapsed': True,
            'label': _('Carrier List'),
            'add_label': _('Add'),
            'endpoint': api_reverse_lazy('hr/carrierlists'),
            'prefilled': {
                'candidate_contact': '{id}',
            }
        }, {
            'query': {
                'candidate_contact': '{id}'
            },
            'type': constants.FIELD_LIST,
            'collapsed': True,
            'label': _('Black List'),
            'add_label': _('Add'),
            'endpoint': api_reverse_lazy('hr/blacklists'),
            'prefilled': {
                'candidate_contact': '{id}',
            }
        }, {
            'query': {
                'candidate_contact': '{id}'
            },
            'type': constants.FIELD_LIST,
            'collapsed': True,
            'label': _('Favorite List'),
            'add_label': _('Add'),
            'endpoint': api_reverse_lazy('hr/favouritelists'),
            'prefilled': {
                'candidate_contact': '{id}',
            }
        }, {
            'query': {
                'candidate_contact': '{id}'
            },
            'type': constants.FIELD_LIST,
            'collapsed': True,
            'label': _('Evaluations'),
            'add_label': _('Add'),
            'endpoint': api_reverse_lazy('hr/candidateevaluations'),
            'prefilled': {
                'candidate_contact': '{id}',
            }
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
                'action': constants.DEFAULT_ACTION_SEND_SMS,
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
        'skill_list', 'tag_list', 'candidate_scores.reliability', 'candidate_scores.loyalty',
        'bmi', 'strength', 'language', 'average_score', 'active_states'
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
            'candidate_scores.reliability', 'candidate_scores.loyalty', 'bmi', 'strength', 'language'
        )
    }]

    search_fields = (
        'contact__title', 'contact__last_name', 'contact__first_name', 'contact__address__city__search_names',
        'contact__address__street_address',
    )

    def get_list_filter(self):
        states_part = partial(
            core_models.WorkflowNode.get_model_all_states, candidate_models.CandidateContact
        )
        list_filter = [{
            'type': constants.FIELD_SELECT,
            'field': 'active_states',
            'choices': lazy(states_part, list),
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


class SkillRelEndpoint(core_endpoints.ApiEndpoint):

    model = candidate_models.SkillRel
    serializer = candidate_serializers.SkillRelSerializer

    list_display = (
        'candidate_contact', 'skill', 'score', 'prior_experience'
    )

    list_editable = (
        {
            'label': _('Skill'),
            'type': constants.FIELD_LINK,
            'field': 'skill',
            'endpoint': format_lazy('{}{{skill.id}}/', api_reverse_lazy('skills/skills')),
        },
        'hourly_rate', 'score', 'prior_experience',
        {
            'label': _('Created'),
            'fields': ('created_at', 'created_by')
        }, {
            'label': _('Updated'),
            'fields': ('updated_at', 'updated_by')
        }, {
            'label': _('Actions'),
            'delim': ' ',
            'fields': ({
                **constants.BUTTON_EDIT,
                'endpoint': format_lazy('{}{{id}}', api_reverse_lazy('candidate/skillrels'))
            }, constants.BUTTON_DELETE)
        },
    )

    fieldsets = (
        {
            'type': constants.FIELD_RELATED,
            'field': 'candidate_contact',
            'hide': True,
        },
        'skill', 'score', 'prior_experience',
        {
            'type': constants.FIELD_LIST,
            'field': 'id_',
            'query': {
                'candidate_skill': '{id}',
            },
            'label': _('Rates'),
            'add_label': _('Add'),
            'endpoint': api_reverse_lazy('candidate/skillraterels'),
            'add_endpoint': api_reverse_lazy('candidate/skillraterels'),
            'prefilled': {
                'candidate_skill': '{id}',
            }
        }
    )

    list_filter = ('candidate_contact', )


class TagRelEndpoint(core_endpoints.ApiEndpoint):

    model = candidate_models.TagRel
    serializer = candidate_serializers.TagRelSerializer

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


class SubcontractorEndpoint(core_endpoints.ApiEndpoint):

    model = candidate_models.Subcontractor
    base_viewset = candidate_viewsets.SubcontractorViewset
    serializer = candidate_serializers.SubcontractorSerializer


class SkillRateRelEndpoint(core_endpoints.ApiEndpoint):

    model = candidate_models.SkillRateRel

    list_editable = (
        {
            'label': _('Rate'),
            'type': constants.FIELD_LINK,
            'field': 'hourly_rate',
            'endpoint': format_lazy('{}{{hourly_rate.id}}/', api_reverse_lazy('skills/skillbaserates')),
        },
        'valid_from', 'valid_until'
    )

    fieldsets = (
        {
            'type': constants.FIELD_RELATED,
            'field': 'candidate_skill',
            'hide': True,
        },
        'hourly_rate', 'valid_from', 'valid_until'
    )

    list_filter = ('candidate_skill', )


router.register(candidate_models.VisaType)
router.register(candidate_models.SuperannuationFund)
router.register(endpoint=CandidateContactEndpoint())
router.register(endpoint=SubcontractorEndpoint())
router.register(endpoint=TagRelEndpoint())
router.register(endpoint=SkillRelEndpoint())
router.register(endpoint=SkillRateRelEndpoint())
router.register(candidate_models.InterviewSchedule)
router.register(candidate_models.CandidateRel)
