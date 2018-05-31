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
from r3sourcer.apps.candidate.api import viewsets as candidate_viewsets, filters as candidate_filters
from r3sourcer.apps.candidate.api import serializers as candidate_serializers


class CandidateContactEndpoint(core_endpoints.ApiEndpoint):

    model = candidate_models.CandidateContact
    base_viewset = candidate_viewsets.CandidateContactViewset
    serializer = candidate_serializers.CandidateContactSerializer
    filter_class = candidate_filters.CandidateContactFilter

    fieldsets = (
        {
            'field': 'id',
            'type': constants.FIELD_INFO,
            'values': {
                'picture': 'contact.picture.thumb',
                'status': {
                    'field': 'active_states',
                    'color': {
                        'danger': [0, 80, 90],
                        'color_attr': 'number',
                    }
                },
                'address': 'contact.address.__str__',
                'available': 'contact.is_available',
                'title': 'contact.__str__',
                'created_at': 'created_at',
                'updated_at': 'updated_at',
            }
        }, {
            'type': constants.CONTAINER_TABS,
            'fields': ({
                'type': constants.CONTAINER_GROUP,
                'label': _('Personal information'),
                'name': _('Personal Info'),
                'main': True,
                'fields': ({
                    'type': constants.CONTAINER_ROW,
                    'fields': (
                        {
                            'type': constants.CONTAINER_GROUP,
                            'label': _('Contacts'),
                            'width': .5,
                            'fields': (
                                {
                                    'field': 'contact.id',
                                    'type': constants.FIELD_TEXT,
                                    'hide': True,
                                }, {
                                    'field': 'contact',
                                    'type': constants.FIELD_RELATED,
                                    'hide': True,
                                }, {
                                    'field': 'contact.address',
                                    'type': constants.FIELD_RELATED,
                                    'hide': True,
                                    'send': False,
                                }, {
                                    'field': 'contact.is_available',
                                    'type': constants.FIELD_CHECKBOX,
                                    'hide': True,
                                    'send': False,
                                }, {
                                    'field': 'contact.first_name',
                                    'type': constants.FIELD_TEXT,
                                    'hide': True,
                                }, {
                                    'field': 'contact.last_name',
                                    'type': constants.FIELD_TEXT,
                                    'hide': True,
                                }, {
                                    'type': constants.FIELD_TEXT,
                                    'field': 'contact.email',
                                    'label': '',
                                    'placeholder': _('E-mail'),
                                }, {
                                    'type': constants.FIELD_TEXT,
                                    'field': 'contact.phone_mobile',
                                    'label': '',
                                    'placeholder': _('Mobile phone'),
                                },),
                        }, {
                            'type': constants.CONTAINER_GROUP,
                            'label': _('Notify'),
                            'width': .25,
                            'fields': (
                                {
                                    'field': 'message_by_email',
                                    'type': constants.FIELD_CHECKBOX,
                                    'label': _('E-Mail'),
                                    'default': False,
                                }, {
                                    'field': 'message_by_sms',
                                    'type': constants.FIELD_CHECKBOX,
                                    'label': _('SMS'),
                                    'default': False,
                                },
                            ),
                        }, {
                            'type': constants.CONTAINER_GROUP,
                            'label': _('Recruitment agent'),
                            'width': .25,
                            'fields': (
                                {
                                    'type': constants.FIELD_RELATED,
                                    'field': 'recruitment_agent',
                                    'endpoint': api_reverse_lazy('core/companycontacts'),
                                    'default': 'session.contact.contact_id',
                                    'label': '',
                                    'query': {
                                        'master_company': 'current',
                                    },
                                }, {
                                    'field': 'recruitment_agent.contact.phone_mobile',
                                    'label': '',
                                    'type': constants.FIELD_TEXT,
                                    'read_only': True,
                                    'send': False,
                                }, {
                                    'field': 'recruitment_agent.contact',
                                    'label': '',
                                    'type': constants.FIELD_TEXT,
                                    'hide': True,
                                    'send': False,
                                }
                            )
                        }
                    )
                }, {
                    'type': constants.CONTAINER_ROW,
                    'fields': (
                        {
                            'type': constants.CONTAINER_GROUP,
                            'label': _('Additional info'),
                            'width': .25,
                            'fields': ('contact.gender', 'language', 'transportation_to_work'),
                        }, {
                            'type': constants.CONTAINER_GROUP,
                            'label': _('Phisical parameters'),
                            'width': .25,
                            'fields': (
                                {
                                    'type': constants.FIELD_TEXT,
                                    'field': 'height',
                                },
                                'weight', 'bmi'
                            ),
                        }, {
                            'type': constants.CONTAINER_GROUP,
                            'label': _('Character'),
                            'width': .25,
                            'fields': (
                                {
                                    'field': 'candidate_scores.id',
                                    'type': constants.FIELD_TEXT,
                                    'send': False,
                                }, {
                                    'field': 'candidate_scores.reliability',
                                    'type': constants.FIELD_SCORE,
                                    'read_only': True,
                                    'label': _('Reliability'),
                                    'send': False,
                                }, {
                                    'field': 'candidate_scores.loyalty',
                                    'type': constants.FIELD_SCORE,
                                    'read_only': True,
                                    'label': _('Loyalty'),
                                    'send': False,
                                }, {
                                    'field': 'strength',
                                    'type': constants.FIELD_SCORE,
                                    'label': _('Strength'),
                                }
                            ),
                        }, {
                            'type': constants.CONTAINER_GROUP,
                            'label': _('Rating'),
                            'width': .25,
                            'fields': (
                                {
                                    'field': 'candidate_scores.recruitment_score',
                                    'type': constants.FIELD_SCORE,
                                    'read_only': True,
                                    'label': _('Recruitment Score'),
                                    'send': False,
                                }, {
                                    'field': 'candidate_scores.client_feedback',
                                    'type': constants.FIELD_SCORE,
                                    'read_only': True,
                                    'label': _('Client Score'),
                                    'send': False,
                                },
                            ),
                        },
                    )
                }, {
                    'type': 'row',
                    'fields': (
                        {
                            'type': constants.CONTAINER_GROUP,
                            'label': _('Residency'),
                            'width': .25,
                            'fields': (
                                'residency',
                                {
                                    'type': constants.FIELD_DATE,
                                    'field': 'visa_expiry_date',
                                    'showIf': [
                                        {
                                            'residency':
                                                candidate_models.CandidateContact.RESIDENCY_STATUS_CHOICES.temporary
                                        }
                                    ],
                                },
                            ),
                        }, {
                            'type': constants.CONTAINER_GROUP,
                            'label': '',
                            'width': .25,
                            'fields': (
                                'nationality',
                                {
                                    'type': constants.FIELD_DATE,
                                    'field': 'vevo_checked_at',
                                    'showIf': [
                                        {
                                            'residency':
                                                candidate_models.CandidateContact.RESIDENCY_STATUS_CHOICES.temporary
                                        }
                                    ],
                                },
                            ),
                        },
                    )
                }, {
                    'type': 'row',
                    'fields': (
                        {
                            'type': constants.CONTAINER_GROUP,
                            'label': _('Formalities'),
                            'width': .25,
                            'fields': (
                                'tax_file_number', 'superannuation_fund',
                                {
                                    'type': constants.FIELD_TEXT,
                                    'field': 'super_member_number',
                                    'showIf': [
                                        'superannuation_fund.id'
                                    ],
                                },
                            ),
                        }, {
                            'type': constants.CONTAINER_GROUP,
                            'label': '',
                            'width': .5,
                            'fields': ('bank_account', 'employment_classification'),
                        }, {
                            'type': constants.CONTAINER_GROUP,
                            'label': _('Emergency'),
                            'width': .25,
                            'fields': ('emergency_contact_name', 'emergency_contact_phone',),
                        },
                    )
                },)
            }, {
                'type': constants.FIELD_LIST,
                'query': {
                    'candidate_contact': '{id}',
                },
                'label': _('Candidate skills'),
                'add_label': _('+ Add item'),
                'endpoint': api_reverse_lazy('candidate/skillrels'),
                'prefilled': {
                    'candidate_contact': '{id}',
                },
                'help': _('Here you can see the skills which belong to the candidate'),
            }, {
                'type': constants.FIELD_LIST,
                'query': {
                    'candidate_contact': '{id}',
                },
                'label': _('Candidate tags'),
                'add_label': _('+ Add item'),
                'endpoint': api_reverse_lazy('candidate/tagrels'),
                'prefilled': {
                    'candidate_contact': '{id}',
                },
                'help': _('Here you can see the tags which belong to the candidate'),
            }, {
                'type': constants.CONTAINER_GROUP,
                'name': _('States'),
                'fields': (
                    {
                        'type': constants.FIELD_TIMELINE,
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
                        'label': _('States history'),
                        'add_label': _('+ Add item'),
                        'endpoint': api_reverse_lazy('core/workflowobjects'),
                        'prefilled': {
                            'object_id': '{id}',
                        },
                        'help': _('Here you can see changes candidate states'),
                    },
                ),
            }, {
                'query': {
                    'contact': '{contact.id}',
                },
                'type': constants.FIELD_LIST,
                'label': _('Unavailabilities'),
                'endpoint': api_reverse_lazy('core/contactunavailabilities'),
            }, {
                'type': constants.FIELD_LIST,
                'query': {
                    'candidate_contact': '{id}'
                },
                'label': _('Job offers'),
                'endpoint': format_lazy('{}candidate/',  api_reverse_lazy('hr/joboffers')),
                'help': _('Here you can see job offers'),
            }, {
                'query': {
                    'candidate_contact': '{id}'
                },
                'type': constants.FIELD_LIST,
                'label': _('Carrier List'),
                'endpoint': api_reverse_lazy('hr/carrierlists'),
                'prefilled': {
                    'candidate_contact': '{id}',
                },
                'help': _('Here you can see information about carrier of candidate'),
            }, {
                'query': {
                    'candidate_contact': '{id}'
                },
                'type': constants.FIELD_LIST,
                'label': _('Black List'),
                'endpoint': api_reverse_lazy('hr/blacklists'),
                'prefilled': {
                    'candidate_contact': '{id}',
                },
            }, {
                'query': {
                    'candidate_contact': '{id}'
                },
                'type': constants.FIELD_LIST,
                'label': _('Favorite List'),
                'endpoint': api_reverse_lazy('hr/favouritelists'),
                'prefilled': {
                    'candidate_contact': '{id}',
                },
                'help': _('Here you can see favorite companies for candidate'),
            }, {
                'query': {
                    'candidate_contact': '{id}'
                },
                'type': constants.FIELD_LIST,
                'label': _('Evaluations'),
                'endpoint': api_reverse_lazy('hr/candidateevaluations'),
                'prefilled': {
                    'candidate_contact': '{id}',
                },
                'help': _('Here you can see evaluations for the candidate'),
            },)
        },
    )

    list_display = (
        {
            'field': 'id',
            'label': _('Personal Info'),
            'type': constants.FIELD_INFO,
            'values': {
                'picture': 'contact.picture.thumb',
                'available': 'contact.is_available',
                'title': 'contact.__str__',
                'address': 'contact.address.__str__',
                'status': {
                    'field': 'active_states',
                    'color_attr': 'number',
                    'color': {
                        'danger': [0, 80, 90],
                    }
                },
            }
        }, {
            'label': _('Contacts'),
            'fields': (
                {
                    'field': 'contact.email',
                    'link': 'mailto:{field}',
                    'type': constants.FIELD_LINK,
                    'label': _('E-mail'),
                }, {
                    'type': constants.FIELD_LINK,
                    'link': 'tel:{field}',
                    'field': 'contact.phone_mobile',
                },
            ),
        }, {
            'type': constants.FIELD_SKILLS,
            'field': 'skill_list',
            'label': _('Skills'),
        }, {
            'type': constants.FIELD_TAGS,
            'field': 'tag_list',
        }, {
            'type': constants.FIELD_SKILLS,
            'field': 'candidate_scores.reliability',
        }, {
            'type': constants.FIELD_SKILLS,
            'field': 'candidate_scores.loyalty',
        }, {
            'type': constants.FIELD_SKILLS,
            'field': 'strength',
        },
        'contact.gender', 'nationality', 'weight', 'height', 'transportation_to_work', 'bmi',
        'language',
    )

    list_tabs = [{
        'label': _('Additional Info'),
        'fields': ('nationality', 'contact.gender', 'language', 'transportation_to_work', )
    }, {
        'label': _('Phisical Parameters'),
        'fields': ('height', 'weight', 'bmi', )
    }, {
        'label': _('Character'),
        'fields': ('candidate_scores.reliability', 'candidate_scores.loyalty', 'strength', )
    }, {
        'label': _('Tags'),
        'fields': ('tag_list', )
    }]

    search_fields = (
        'contact__title', 'contact__last_name', 'contact__first_name', 'contact__address__city__search_names',
        'contact__address__street_address',
    )

    def get_list_filter(self):
        states_part = partial(
            core_models.WorkflowNode.get_model_all_states, candidate_models.CandidateContact
        )
        list_filter = [
            {
                'type': constants.FIELD_RELATED,
                'field': 'skill',
                'label': _('Skills'),
                'endpoint': api_reverse_lazy('skills/skills'),
                'multiple': True,
            }, {
                'type': constants.FIELD_RELATED,
                'field': 'tag',
                'label': _('Tags'),
                'endpoint': api_reverse_lazy('core/tags'),
                'multiple': True,
            }, {
                'type': constants.FIELD_SELECT,
                'field': 'active_states',
                'choices': lazy(states_part, list),
                'multiple': True,
            }, {
                'type': constants.FIELD_CHECKBOX,
                'field': 'contact.gender',
                'multiple': True,
            }, {
                'type': constants.FIELD_RELATED,
                'field': 'recruitment_agent',
                'label': _('Recruitment agent'),
                'endpoint': api_reverse_lazy('core/companycontacts'),
            }, {
                'field': 'candidate_scores.average_score',
                'label': _('Overal score'),
                'type': constants.FIELD_RANGE,
                'max': 5,
            }, {
                'type': constants.FIELD_CHECKBOX,
                'field': 'transportation_to_work',
                'multiple': True,
            }, {
                'field': 'created_at',
                'type': constants.FIELD_DATE,
            }
        ]

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
        }, {
            'type': constants.FIELD_RELATED,
            'field': 'skill',
            'read_only': False,
        },
        'score', 'prior_experience',
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
        }, {
            'label': _('Actions'),
            'fields': ({
                **constants.BUTTON_EDIT,
                'endpoint': format_lazy('{}{{id}}', api_reverse_lazy('candidate/tagrels'))
            }, constants.BUTTON_DELETE)
        }
    )

    fieldsets = (
        {
            'type': constants.FIELD_RELATED,
            'field': 'candidate_contact',
            'hide': True,
        }, {
            'type': constants.FIELD_RELATED,
            'field': 'tag',
            'read_only': False,
        },
        'verification_evidence', 'verified_by',
    )

    list_filter = ('candidate_contact', )


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
        }, {
            'type': constants.FIELD_RELATED,
            'field': 'hourly_rate',
            'query': {
                'candidate_skill': '{candidate_skill.id}',
            },
        },
        'valid_from', 'valid_until'
    )

    list_filter = ('candidate_skill', )


class SuperannuationFundEndpoint(core_endpoints.ApiEndpoint):

    model = candidate_models.SuperannuationFund

    fieldsets = ('name', 'membership_number')

    search_fields = ['name']


router.register(candidate_models.VisaType)
router.register(endpoint=SuperannuationFundEndpoint())
router.register(endpoint=CandidateContactEndpoint())
router.register(endpoint=SubcontractorEndpoint())
router.register(endpoint=TagRelEndpoint())
router.register(endpoint=SkillRelEndpoint())
router.register(endpoint=SkillRateRelEndpoint())
router.register(candidate_models.InterviewSchedule)
router.register(candidate_models.CandidateRel)
