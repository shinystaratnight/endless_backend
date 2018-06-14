from functools import partial

from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.utils.functional import lazy
from django.utils.translation import ugettext_lazy as _
from drf_auto_endpoint.router import router
from drf_auto_endpoint.decorators import bulk_action
from rest_framework.response import Response
from rest_framework.exceptions import ParseError

from r3sourcer.apps.core import models
from r3sourcer.apps.core.api import serializers, viewsets, filters
from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.core.models.constants import CANDIDATE, CLIENT, MANAGER
from r3sourcer.apps.core.utils.text import format_lazy
from r3sourcer.apps.core_adapter import constants
from r3sourcer.apps.core_adapter.utils import api_reverse_lazy


class ContactEndpoint(ApiEndpoint):
    model = models.Contact
    base_viewset = viewsets.ContactViewset
    serializer = serializers.ContactSerializer
    filter_class = filters.ContactFilter
    search_fields = (
        'title',
        'first_name',
        'last_name',
        'address__city__search_names',
        'email',
        'phone_mobile',
    )

    list_display = (
        {
            'field': 'id',
            'label': _('Personal Info'),
            'type': constants.FIELD_INFO,
            'values': {
                'picture': 'picture.thumb',
                'available': 'availability',
                'title': '__str__',
                'address': 'address.__str__',
            }
        }, {
            'label': _('Contact'),
            'fields': (
                {
                    'field': 'email',
                    'link': 'mailto:{field}',
                    'type': constants.FIELD_LINK,
                    'label': _('E-mail'),
                }, {
                    'type': constants.FIELD_LINK,
                    'link': 'tel:{field}',
                    'field': 'phone_mobile',
                }
            ),
        }, {
            'label': _('Relations'),
            'fields': (
                {
                    'display': _('Candidate'),
                    'field': 'candidate_contacts',
                    'inline': True,
                    'type': constants.FIELD_LINK,
                    'endpoint': format_lazy(
                        '{}{{candidate_contacts.id}}', api_reverse_lazy('candidate/candidatecontacts')
                    ),
                }, {
                    'display': _('Company Contact'),
                    'field': 'company_contact',
                    'inline': True,
                    'type': constants.FIELD_LINK,
                    'endpoint': format_lazy('{}{{company_contact.id}}', api_reverse_lazy('core/companycontacts')),
                }, {
                    'display': _('Master Company'),
                    'field':  'master_company',
                    'inline': True,
                    'type': constants.FIELD_LINK,
                    'endpoint': format_lazy('{}{{candidate_contacts.id}}', api_reverse_lazy('core/companies')),
                }
            )
        }
    )

    fieldsets_add = (
        {
            'type': constants.CONTAINER_ROW,
            'label': _('General'),
            'fields': (
                {
                    'type': constants.CONTAINER_COLUMN,
                    'fields': ('title', 'first_name', 'last_name', 'gender'),
                }, {
                    'type': constants.CONTAINER_COLUMN,
                    'fields': (
                        'email', 'phone_mobile',
                        {
                            'type': constants.FIELD_DATE,
                            'field': 'birthday',
                            'help': _('Optional for Client Contacts, must be filled for Candidate contacts'),
                        }, {
                            'type': constants.FIELD_ADDRESS,
                            'field': 'address',
                            'edit': True,
                            'delete': False,
                            'create': False,
                            'endpoint': api_reverse_lazy('core/addresses')
                        },
                    ),
                },
            ),
        },
    )

    fieldsets = (
        {
            'type': constants.CONTAINER_ROW,
            'label': '{title} {first_name} {last_name}',
            'fields': (
                {
                    'type': constants.CONTAINER_COLUMN,
                    'fields': (
                        {
                            'type': constants.FIELD_PICTURE,
                            'field': 'picture',
                            'label': _('Profile Picture'),
                            'label_upload': _('Choose a file'),
                            'label_photo': _('Take a photo'),
                            'custom': [],
                        },
                    ),
                }, {
                    'type': constants.CONTAINER_COLUMN,
                    'fields': (
                        {
                            'type': constants.FIELD_RELATED,
                            'field': 'id',
                            'read_only': True,
                            'label': '',
                            'send': False,
                            'custom': ('address.__str__', 'phone_mobile', 'email'),
                        },
                    ),
                },
            ),
        },
    ) + fieldsets_add + (
        {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Misc'),
            'fields': ('is_available', 'phone_mobile_verified', 'email_verified')
        }, {
            'query': {
                'object_id': '{id}',
            },
            'type': constants.FIELD_LIST,
            'collapsed': True,
            'label': _('Notes'),
            'add_label': _('Add'),
            'endpoint': api_reverse_lazy('core/notes'),
            'prefilled': {
                'object_id': '{id}',
            },
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Relations'),
            'fields': ({
                'type': constants.FIELD_RELATED,
                'label': _('User'),
                'field': 'user',
                'read_only': True,
                'send': False,
                'metadata_query': {
                    'fieldsets_type': 'contact',
                },
            }, {
                'type': constants.FIELD_RELATED,
                'label': _('Candidate Contact'),
                'field': 'candidate_contacts',
                'send': False,
                'read_only': False,
                'endpoint': api_reverse_lazy('candidate/candidatecontacts'),
                'prefilled': {
                    'contact': '{id.id}',
                },
                'add_metadata_query': {
                    'fieldsets_type': 'contact',
                }
            }, {
                'type': constants.FIELD_RELATED,
                'label': _('Recruitment Agent'),
                'field': 'candidate_contacts.recruitment_agent',
                'send': False,
                'read_only': True,
            }, {
                'type': constants.FIELD_RELATED,
                'label': _('Company Contact'),
                'field': 'company_contact',
                'send': False,
                'read_only': False,
                'endpoint': api_reverse_lazy('core/companycontacts'),
                'prefilled': {
                    'contact': '{id.id}',
                },
                'add': True,
                'edit': True,
            }, {
                'type': constants.FIELD_RELATED,
                'label': _('Master Company'),
                'field': 'master_company',
                'endpoint': api_reverse_lazy('core/companies'),
                'send': False,
                'read_only': True,
            },),
        }
    )

    def get_list_filter(self):
        au_regions = partial(models.Region.get_countrys_regions, 'AU')
        types = [{'label': t.capitalize(), 'value': t} for t in (CANDIDATE, CLIENT, MANAGER)]
        return [
            {
                'type': constants.FIELD_SELECT,
                'field': 'state',
                'label': _('State'),
                'choices': lazy(au_regions, list),
            }, {
                'type': constants.FIELD_SELECT,
                'field': 'contact_type',
                'label': _('Type of Contact'),
                'choices': types,
            },
            'is_available', 'phone_mobile_verified', 'email_verified',
        ]


class CompanyAddressEndpoint(ApiEndpoint):

    model = models.CompanyAddress
    base_viewset = viewsets.CompanyAddressViewset
    base_serializer = serializers.CompanyAddressSerializer
    filter_class = filters.CompanyAddressFilter

    list_label = ('Client Company Address')
    pagination_label = ('Client Company Addresses')

    list_display = (
        {
            'label': _('Company'),
            'fields': ({
                'type': constants.FIELD_LINK,
                'endpoint': format_lazy(
                    '{}{{company.id}}/',
                    api_reverse_lazy('core/companies')
                ),
                'field': 'company.name',
            }, {
                'type': constants.FIELD_BUTTON,
                'icon': 'fa-external-link',
                'label': '%s:' % _('Invoices'),
                'text': '{field}',
                'endpoint': format_lazy(
                    '{}?company={{company.id}}',
                    api_reverse_lazy('core/invoices')
                ),
                'field': 'invoices_count',
                'action': constants.DEFAULT_ACTION_LIST,
            }, {
                'type': constants.FIELD_BUTTON,
                'icon': 'fa-external-link',
                'label': '%s:' % _('Orders'),
                'text': '{field}',
                'endpoint': format_lazy(
                    '{}?provider_company={{company.id}}',
                    api_reverse_lazy('core/orders')
                ),
                'field': 'orders_count',
                'action': constants.DEFAULT_ACTION_LIST,
            }),
        },
        {
            'label': _('Branch'),
            'fields': ({
                'type': constants.FIELD_LINK,
                'endpoint': '/',
                'fields': ({
                    'field': 'hq',
                    'values': {
                        True: 'HQ:',
                    }
                }, 'address.__str__'),
            }, {
                'type': constants.FIELD_BUTTON,
                'action': 'openMap',
                'text': _('Open map'),
                'icon': 'fa-globe',
                'fields': ('address.latitude', 'address.longitude')
            }),
        },
        (
            _('Primary Contact'),
            ({
                'type': constants.FIELD_LINK,
                'field': 'primary_contact.contact.__str__',
                'endpoint': '/',
            }, {
                'type': constants.FIELD_LINK,
                'link': 'tel:{field}',
                'field': 'primary_contact.contact.phone_mobile',
            }, {
                'type': constants.FIELD_BUTTON,
                'action': constants.DEFAULT_ACTION_SEND_SMS,
                'text': _('SMS'),
                'icon': 'fa-commenting',
                'fields': ('primary_contact.contact.phone_mobile',)
            })
        ),
        {
            'label': _('Portfolio Manager'),
            'field': 'portfolio_manager',
            'type': constants.FIELD_LINK,
            'endpoint': '/',
        },
        {
            'label': _('State'),
            'field': 'active_states',
        },
        {
            'label': _('Credit'),
            'fields': ({
                'type': constants.FIELD_LINK,
                'endpoint': '/',
                'fields': (
                    'company.credit_check', 'company.approved_credit_limit',
                    'company.get_terms_of_payment'
                ),
            },),
        },
        {
            'label': _('Journal'),
            'fields': ({
                'type': constants.FIELD_BUTTON,
                'endpoint': api_reverse_lazy('core/companyaddresses',
                                             'log'),
                'text': _('Open Journal'),
                'action': constants.DEFAULT_ACTION_LIST,
                'field': 'id',
            },),
        }
    )

    list_editable = (
        'name', {
            'label': _('Address'),
            'type': constants.FIELD_LINK,
            'field': 'address',
            'endpoint': format_lazy(
                '{}{{address.id}}/',
                api_reverse_lazy('core/addresses')
            ),
        }, 'hq', {
            'label': _('Primary Contact'),
            'type': constants.FIELD_LINK,
            'field': 'primary_contact',
            'endpoint': format_lazy(
                '{}{{primary_contact.id}}/',
                api_reverse_lazy('core/companycontacts')
            ),
        },
        'phone_landline', 'phone_fax', 'active',
        {
            'label': _('Actions'),
            'fields': ({
                **constants.BUTTON_EDIT,
                'endpoint': format_lazy('{}{{id}}', api_reverse_lazy('core/companyaddresses'))
            }, constants.BUTTON_DELETE)
        }
    )

    fieldsets = (
        'name', 'company',
        {
            'type': constants.FIELD_ADDRESS,
            'field': 'address',
        },
        'hq', 'phone_landline', 'phone_fax',
        {
            'type': constants.FIELD_RELATED,
            'field': 'primary_contact',
            'prefilled': {
                'company': '{company.id}',
            },
            'query': {
                'company': '{company.id}',
            },
        },
        'active'
    )

    # FIXME: add for remaining columns and change to real labels and endpoints
    context_actions = {
        'primary_contact': [{
            'label': _('Send SMS'),
            'endpoint': '/',
        }, {
            'label': _('Add New Company Contact'),
            'endpoint': '/',
        }, {
            'label': _('Manage Branch Contacts'),
            'endpoint': '/',
        }, {
            'label': _('Add Note'),
            'endpoint': '/',
        }, {
            'label': _('Add Activity'),
            'endpoint': '/',
        }],

        'portfolio_manager': [{
            'label': _('Create Activity for PM'),
            'endpoint': '/',
        }, {
            'label': _('Reassign'),
            'endpoint': '/',
        }],

        'credit': [{
            'label': _('Reupload evidence'),
            'endpoint': '/',
        }, {
            'label': _('Fill in credit approval information'),
            'endpoint': '/',
        }],
    }

    highlight = {
        'field': 'company.type',
        'values': ('master', ),
    }

    ordering_mapping = {'company': 'company.name'}

    # FIXME: change to real filters
    def get_list_filter(self):
        states_part = partial(
            models.WorkflowNode.get_model_all_states, models.CompanyRel
        )
        list_filter = ['company', 'primary_contact.contact', {
            'type': constants.FIELD_SELECT,
            'field': 'active_states',
            'choices': lazy(states_part, list),
        }, {
            'type': constants.FIELD_RELATED,
            'field': 'portfolio_manager',
            'endpoint': api_reverse_lazy('core/companycontacts'),
        }, {
            'field': 'updated_at',
            'type': constants.FIELD_DATE,
        }]

        return list_filter

    # FIXME: add/change to real actions
    @bulk_action(method='POST', text=_('Delete selected'))
    def delete(self, request, *args, **kwargs):
        ids = request.data

        if not ids:
            raise ParseError(_('Objects not selected'))

        return Response({
            'status': 'success',
            'message': _('Deleted successfully'),
        })

    @bulk_action(method='POST', text=_('Send sms'), confirm=False)
    def sendsms(self, request, *args, **kwargs):
        id_list = request.data

        if not id_list or not isinstance(id_list, list):
            raise ParseError(_('You should select Company addresses'))

        phone_numbers = set(models.CompanyAddress.objects.filter(
            id__in=id_list, primary_contact__contact__phone_mobile__isnull=False).values_list(
            'primary_contact__contact__phone_mobile', flat=True))

        return Response({
            'status': 'success',
            'phone_number': phone_numbers,
            'message': _('Phones numbers was selected'),
        })


class CompanyEndpoint(ApiEndpoint):

    model = models.Company
    base_viewset = viewsets.CompanyViewset
    base_serializer = serializers.CompanyListSerializer
    filter_class = filters.CompanyFilter

    list_label = _('Client')
    pagination_label = _('Clients')

    fields = (
        '__all__',
        {
            'invoice_rule': '__all__',
            'manager': (
                'id', '__str__', 'job_title', {
                    'contact': ('id', '__str__', 'email', 'phone_mobile'),
                },
            ),
            'groups': ('id', '__str__')
        }
    )

    list_display = (
        {
            'field': 'id',
            'label': _('Client Info'),
            'type': constants.FIELD_INFO,
            'values': {
                'picture': 'logo.thumb',
                'available': 'available',
                'title': 'name',
                'address': 'address.__str__',
                'description': 'description',
            }
        }, {
            'label': _('Primary Contact'),
            'fields': (
                {
                    'type': constants.FIELD_LINK,
                    'field': 'manager.contact',
                    'display': '{manager.job_title}',
                    'endpoint': format_lazy('{}{{manager.id}}/', api_reverse_lazy('core/companycontacts')),
                }, {
                    'field': 'manager.contact.email',
                    'link': 'mailto:{field}',
                    'type': constants.FIELD_LINK,
                    'label': _('E-mail'),
                }, {
                    'type': constants.FIELD_LINK,
                    'link': 'tel:{field}',
                    'field': 'manager.contact.phone_mobile',
                }
            ),
        }, {
            'label': _('Manager'),
            'type': constants.FIELD_LINK,
            'field': 'primary_contact',
            'display': '{primary_contact.job_title}',
            'endpoint': format_lazy('{}{{primary_contact.id}}/', api_reverse_lazy('core/companycontacts')),
        }, {
            'label': _('Credit Info'),
            'fields': ({
                'type': constants.FIELD_STATIC,
                'field': 'credit_approved',
            }, {
                'field': 'credit_check',
                'type': constants.FIELD_ICON,
                'values': {
                    True: 'circle',
                    False: 'circle',
                },
                'color': {
                    False: 'danger',
                    True: 'success',
                },
            }, {
                'type': constants.FIELD_STATIC,
                'field': 'approved_credit_limit',
            }, {
                'type': constants.FIELD_STATIC,
                'field': 'terms_of_pay',
            }),
        }, {
            'label': _('Company State'),
            'type': constants.FIELD_TAGS,
            'field': 'active_states',
            'color_attr': 'number',
            'outline': True,
            'color': {
                'danger': [0, 80, 90],
            }
        },
    )

    fieldsets_add = ('name', 'business_id', )

    fieldsets = (
        {
            'type': constants.CONTAINER_ROW,
            'label': '{name}',
            'fields': (
                {
                    'type': constants.CONTAINER_COLUMN,
                    'fields': ({
                        'type': constants.FIELD_PICTURE,
                        'field': 'logo',
                        'label': _('Logo'),
                        'file': False,
                        'label_upload': _('Choose a file'),
                        'label_photo': _('Take a photo'),
                        'custom': [],
                    },)
                }, {
                    'type': constants.CONTAINER_COLUMN,
                    'fields': ({
                        'type': constants.FIELD_RELATED,
                        'field': 'id',
                        'read_only': True,
                        'label': _('Client'),
                        'custom': ('name', 'website'),
                    },)
                }, {
                    'type': constants.CONTAINER_COLUMN,
                    'fields': ({
                        'type': constants.FIELD_RELATED,
                        'field': 'id',
                        'read_only': True,
                        'label': _('Primary Contact'),
                        'custom': (
                            'manager.job_title', 'manager.contact.__str__',
                            'manager.contact.phone_mobile', 'manager.contact.email'
                        ),
                    },)
                },
            ),
        }, {
            'type': constants.CONTAINER_ROW,
            'label': _('General'),
            'collapsed': False,
            'fields': (
                {
                    'type': constants.CONTAINER_COLUMN,
                    'fields': (
                        'name', 'website', {
                            'label': _('Primary Contact'),
                            'type': constants.FIELD_RELATED,
                            'field': 'manager',
                            'endpoint': api_reverse_lazy('core/companycontacts'),
                            'prefilled': {
                                'company': '{id.id}',
                            },
                            'query': {
                                'company': '{id.id}',
                            },
                        }, {
                            'label': _('Master company'),
                            'type': constants.FIELD_RELATED,
                            'field': 'master_company',
                            'endpoint': api_reverse_lazy('core/companies'),
                            'read_only': False,
                            'showIf': [
                                {'type': 'regular'}
                            ],
                            'query': {
                                'type': 'master',
                            },
                        }, {
                            'label': _('Portfolio Manager'),
                            'type': constants.FIELD_RELATED,
                            'field': 'primary_contact',
                            'read_only': False,
                            'add': False,
                            'endpoint': api_reverse_lazy('core/companycontacts'),
                            'showIf': [
                                {'type': 'regular'}
                            ],
                            'query': {
                                'company': '{master_company.id}',
                            },
                        }, {
                            'type': constants.FIELD_TEXT,
                            'field': 'type',
                            'hide': True,
                        }
                    ),
                }, {
                    'type': constants.CONTAINER_COLUMN,
                    'fields': (
                        'business_id', 'registered_for_gst',
                        {
                            'field': 'industry',
                            'type': constants.FIELD_RELATED,
                            'read_only': False,
                        }, {
                            'field': 'description',
                            'type': constants.FIELD_TEXTAREA,
                        }
                    ),
                },
            ),
        }, {
            'query': {
                'company': '{id}'
            },
            'type': constants.FIELD_LIST,
            'label': _('Client Company Address'),
            'add_label': _('Add'),
            'endpoint': api_reverse_lazy('core/companyaddresses'),
            'prefilled': {
                'company': '{id}',
            },
            'delay': True,
        }, {
            'query': {
                'company': '{id}'
            },
            'type': constants.FIELD_LIST,
            'collapsed': True,
            'label': _('Client Contacts'),
            'add_label': _('Add'),
            'endpoint': api_reverse_lazy('core/companycontactrelationships'),
            'add_endpoint': api_reverse_lazy('core/companycontacts'),
            'prefilled': {
                'company': '{id}',
            }
        }, {
            'type': constants.FIELD_LIST,
            'collapsed': True,
            'query': {
                'company': '{id}',
            },
            'label': _('Jobsites'),
            'add_label': _('Add'),
            'endpoint': api_reverse_lazy('hr/jobsites'),
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Credit info'),
            'fields': (
                {
                    'type': constants.FIELD_PICTURE,
                    'field': 'credit_check_proof',
                    'label_upload': _('Choose a file'),
                    'label_photo': _('Take a photo'),
                }, 'credit_check',
                {
                    'label': _('Approval date'),
                    'type': constants.FIELD_DATE,
                    'field': 'credit_check_date',
                }, 'approved_credit_limit',
                'terms_of_payment', 'payment_due_date',
            )
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Banking details'),
            'fields': ('billing_email', ),
        }, {
            'type': constants.FIELD_LIST,
            'collapsed': True,
            'query': {
                'company': '{id}',
            },
            'label': _('Price list'),
            'add_label': _('Add'),
            'endpoint': api_reverse_lazy('pricing/pricelists'),
            'prefilled': {
                'company': '{id}',
            },
            'metadata_query': {
                'editable_type': 'company',
            },
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': False,
            'name': _('State'),
            'fields': (
                {
                    'type': constants.FIELD_TIMELINE,
                    'label': _('States Timeline'),
                    'field': 'id',
                    'endpoint': format_lazy('{}timeline/', api_reverse_lazy('core/workflownodes')),
                    'query': {
                        'model': 'core.companyrel',
                        'object_id': '{regular_company_rel.id}',
                    },
                },
            )
        }, {
            'type': constants.FIELD_LIST,
            'query': {
                'object_id': '{regular_company_rel.id}'
            },
            'collapsed': True,
            'label': _('States History'),
            'add_label': _('Add'),
            'endpoint': api_reverse_lazy('core/workflowobjects'),
            'prefilled': {
                'object_id': '{regular_company_rel.id}',
            }
        }, {
            'query': {
                'object_id': '{id}',
            },
            'type': constants.FIELD_LIST,
            'collapsed': True,
            'label': _('Notes'),
            'add_label': _('Add'),
            'endpoint': api_reverse_lazy('core/notes'),
            'prefilled': {
                'object_id': '{id}',
            },
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Invoice Rule'),
            'fields': (
                {
                    'field': 'invoice_rule.id',
                    'type': constants.FIELD_TEXT,
                    'hidden': True,
                    'read_only': True,
                },
                'invoice_rule.separation_rule',
                {
                    'field': 'invoice_rule.period',
                    'type': constants.FIELD_SELECT,
                    'label': _('Invoice Frequency'),
                }, {
                    'field': 'invoice_rule.period_zero_reference',
                    'type': constants.FIELD_TEXT,
                    'showIf': [
                        {
                            'type': str(models.Company.COMPANY_TYPES.master),
                        }
                    ]
                }, {
                    'field': 'invoice_rule.serial_number',
                    'type': constants.FIELD_TEXT,
                    'showIf': [
                        {
                            'type': str(models.Company.COMPANY_TYPES.master),
                        }
                    ]
                }, {
                    'field': 'invoice_rule.starting_number',
                    'type': constants.FIELD_TEXT,
                    'showIf': [
                        {
                            'type': str(models.Company.COMPANY_TYPES.master),
                        }
                    ]
                }, {
                    'field': 'invoice_rule.notice',
                    'type': constants.FIELD_TEXT,
                    'showIf': [
                        {
                            'type': str(models.Company.COMPANY_TYPES.master),
                        }
                    ]
                }, {
                    'field': 'invoice_rule.comment',
                    'type': constants.FIELD_TEXT,
                    'showIf': [
                        {
                            'type': str(models.Company.COMPANY_TYPES.master),
                        }
                    ]
                },
                'invoice_rule.show_candidate_name',
            )
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Other'),
            'fields': ('timesheet_approval_scheme', )
        },
    )

    search_fields = (
        'name', 'company_addresses__address__street_address', 'company_addresses__address__city__search_names',
        'notes', 'description'
    )

    def get_list_filter(self):
        au_regions = partial(models.Region.get_countrys_regions, 'AU')
        states_part = partial(models.WorkflowNode.get_model_all_states, models.CompanyRel)
        list_filter = [{
            'type': constants.FIELD_SELECT,
            'field': 'status',
            'label': _('Status'),
            'choices': lazy(states_part, list),
        }, {
            'type': constants.FIELD_RELATED,
            'field': 'portfolio_manager',
            'label': _('Portfolio Manager'),
            'endpoint': api_reverse_lazy('core/companycontacts'),
        }, {
            'type': constants.FIELD_SELECT,
            'field': 'state',
            'label': _('State'),
            'choices': lazy(au_regions, list),
        }, {
            'type': constants.FIELD_SELECT,
            'field': 'credit_check',
            'choices': [{'label': 'Approved', 'value': 'True'},
                        {'label': 'Unapproved', 'value': 'False'}]
        }, {
            'field': 'approved_credit_limit',
            'label': _('Credit Limit'),
            'type': constants.FIELD_RANGE,
        }]

        return list_filter


class CompanyContactRelationEndpoint(ApiEndpoint):

    model = models.CompanyContactRelationship
    serializer = serializers.CompanyContactRelationshipSerializer
    filter_class = filters.CompanyContactRelationshipFilter

    list_editable = (
        'company_contact.job_title', 'company_contact.contact.first_name', 'company_contact.contact.last_name',
        'company_contact.contact.phone_mobile', 'company_contact.contact.email',
        'company_contact.receive_job_confirmation_sms',
        {
            'label': _('Actions'),
            'fields': ({
                **constants.BUTTON_EDIT,
                'endpoint': format_lazy('{}{{company_contact.id}}', api_reverse_lazy('core/companycontacts'))
            }, constants.BUTTON_DELETE)
        },
    )

    list_label = ('Client Contact Relations')
    pagination_label = ('Client Contacts')

    fieldsets = (
        {
            'type': constants.FIELD_TEXT,
            'field': 'company',
            'hide': True,
        },
        'company_contact', 'active',
        {
            'type': constants.FIELD_DATE,
            'field': 'termination_date',
        }
    )


class CompanyContactEndpoint(ApiEndpoint):

    model = models.CompanyContact
    base_viewset = viewsets.CompanyContactViewset
    serializer = serializers.CompanyContactRenderSerializer
    filter_class = filters.CompanyContactFilter

    list_label = _('Client Contact')
    pagination_label = _('Client Contacts')

    list_display = (
        'job_title', 'contact.title', 'contact.first_name',
        'contact.last_name',
        {
            'label': _('Mobile Phone'),
            'fields': (
                {
                    'type': constants.FIELD_LINK,
                    'link': 'tel:{field}',
                    'field': 'contact.phone_mobile',
                },
                {
                    'type': constants.FIELD_BUTTON,
                    'action': constants.DEFAULT_ACTION_SEND_SMS,
                    'text': _('SMS'),
                    'icon': 'fa-commenting',
                    'fields': ('contact.phone_mobile',)
                }
            ),
        },
        'contact.email',
        'receive_job_confirmation_sms'
    )

    _base_fieldsets = (
        {
            'type': constants.FIELD_RELATED,
            'field': 'company',
            'label': _('Client'),
            'endpoint': api_reverse_lazy('core/companies'),
            'read_only': False,
            'required': True,
        }, {
            'type': constants.FIELD_RELATED,
            'field': 'contact',
            'showIf': ['company.id'],
            'checkObject': {
                'query': {
                    'company': '{company.id}',
                    'contact': '{contact.id}',
                    'active': True,
                },
                'endpoint': api_reverse_lazy('core/companycontactrelationships'),
                'error': _('This client contact already exists!'),
            }
        },
        'job_title',
    )

    fieldsets_add = _base_fieldsets
    fieldsets = (
        {
            'field': 'id',
            'type': constants.FIELD_INFO,
            'values': {
                'picture': 'contact.picture.thumb',
                'company': 'company.__str__',
                'available': 'contact.is_available',
                'title': 'contact.__str__',
                'job_title': 'job_title',
                'created_at': 'created_at',
                'updated_at': 'updated_at',
            }
        }, {
            'type': constants.CONTAINER_TABS,
            'fields': ({
                'type': constants.CONTAINER_GROUP,
                'label': _('General information'),
                'name': _('General Info'),
                'main': True,
                'fields': ({
                    'type': constants.CONTAINER_ROW,
                    'fields': (
                        {
                            'type': constants.CONTAINER_GROUP,
                            'label': '',
                            'width': .25,
                            'fields': (
                                {
                                    'field': 'rating_unreliable',
                                    'type': constants.FIELD_CHECKBOX,
                                    'label': _('Rating ureliable'),
                                    'default': False,
                                }, {
                                    'field': 'receive_job_confirmation_sms',
                                    'type': constants.FIELD_CHECKBOX,
                                    'label': _('Receive Job confirmation SMS'),
                                    'default': False,
                                }, {
                                    'field': 'active',
                                    'type': constants.FIELD_CHECKBOX,
                                    'label': _('Active'),
                                    'default': False,
                                }, {
                                    'type': constants.FIELD_DATE,
                                    'field': 'termination_date',
                                },
                            ),
                        },
                    ),
                },)
            }, {
                'query': {
                    'primary_contact': '{id}',
                },
                'type': constants.FIELD_LIST,
                'label': _('Jobsites'),
                'add_label': _('Add'),
                'endpoint': api_reverse_lazy('hr/jobsites'),
                'prefilled': {
                    'primary_contact': '{id}',
                },
            }, {
                'query': {
                    'customer_representative': '{id}',
                },
                'type': constants.FIELD_LIST,
                'label': _('Jobs'),
                'add_label': _('Add'),
                'endpoint': api_reverse_lazy('hr/jobs'),
                'prefilled': {
                    'customer_representative': '{id}',
                },
            }, {
                'query': {
                    'supervisor': '{id}',
                },
                'type': constants.FIELD_LIST,
                'label': _('Timesheets'),
                'endpoint': api_reverse_lazy('hr/timesheets'),
                'metadata_query': {
                    'editable_type': 'supervisor',
                }
            }, {
                'query': {
                    'object_id': '{id}',
                },
                'type': constants.FIELD_LIST,
                'label': _('Notes'),
                'add_label': _('Add'),
                'endpoint': api_reverse_lazy('core/notes'),
                'prefilled': {
                    'object_id': '{id}',
                },
            },)
        },
    )

    search_fields = ('job_title', 'contact__title', 'contact__first_name', 'contact__last_name')

    def _get_all_job_titles(self):
        return [
            {'label': jt, 'value': jt}
            for jt in models.CompanyContact.objects.all().values_list(
                'job_title', flat=True).distinct()
        ]

    def get_list_filter(self):
        return [{
            'type': constants.FIELD_SELECT,
            'field': 'job_title',
            'choices': self._get_all_job_titles,
            'is_qs': True,
        }, {
            'type': constants.FIELD_RELATED,
            'field': 'company',
            'endpoint': api_reverse_lazy('core/companies'),
        }, {
            'type': constants.FIELD_RELATED,
            'field': 'manager',
            'endpoint': format_lazy(
                '{}?is_manager=3',
                api_reverse_lazy('core/companycontacts')
            ),
        }]

    @bulk_action(method='POST', text=_('Send sms'), confirm=False)
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


class CompanyRelEndpoint(ApiEndpoint):

    model = models.CompanyRel
    list_display = ('master_company', 'regular_company', 'primary_contact', )
    fieldsets = (
        'master_company', 'regular_company', 'primary_contact',
        {
            'type': constants.FIELD_TIMELINE,
            'label': _('States Timeline'),
            'field': 'id',
            'endpoint': format_lazy(
                '{}timeline/',
                api_reverse_lazy('core/workflownodes'),
            ),
            'query': {
                'model': 'core.companyrel',
                'object_id': '{id}',
            },
        }
    )


class CompanyLocalizationEndpoint(ApiEndpoint):

    model = models.CompanyLocalization
    filter_class = filters.CompanyLocalizationFilter


class SiteEndpoint(ApiEndpoint):

    model = Site
    base_viewset = viewsets.SiteViewset


class NavigationEndpoint(ApiEndpoint):

    model = models.ExtranetNavigation
    base_viewset = viewsets.NavigationViewset
    serializer = serializers.NavigationSerializer


class WorkflowEndpoint(ApiEndpoint):

    model = models.Workflow
    search_fields = ('name', 'model__app_label', 'model__model', )
    fieldsets = ('name', 'model', )

    list_display = ('name', 'model', )


class WorkflowNodeEndpoint(ApiEndpoint):

    model = models.WorkflowNode
    base_viewset = viewsets.WorkflowNodeViewset
    serializer = serializers.WorkflowNodeSerializer
    filter_class = filters.WorkflowNodeFilter

    search_fields = (
        'workflow__name', 'company__name', 'number', 'name_before_activation', 'name_after_activation'
    )
    list_filter = ('workflow.model', )

    fieldsets = (
        'workflow', 'number', 'name_before_activation',
        'name_after_activation', {
            'type': constants.FIELD_RULE,
            'field': 'rules',
        }, 'company', 'active', 'hardlock',
    )
    list_display = (
        'workflow', 'company', 'number', 'name_before_activation', 'name_after_activation', 'active', 'hardlock',
    )


class WorkflowObjectEndpoint(ApiEndpoint):

    model = models.WorkflowObject
    serializer = serializers.WorkflowObjectSerializer
    filter_class = filters.WorkflowObjectFilter

    fieldsets = ({
        'type': constants.FIELD_TEXT,
        'field': 'object_id',
        'hide': True,
    }, 'state', {
        'type': constants.FIELD_TEXTAREA,
        'field': 'comment'
    }, 'active')

    list_filter = ('object_id', 'active', 'state.workflow.name')

    list_display = ('state_name', 'comment', 'active')
    list_editable = (
        'state_name', 'comment', 'active',
        {
            'label': _('Created'),
            'fields': ('created_at', 'created_by')
        }, {
            'label': _('Updated'),
            'fields': ('updated_at', 'updated_by')
        }
    )


class DashboardModuleEndpoint(ApiEndpoint):

    model = models.DashboardModule
    base_viewset = viewsets.DashboardModuleViewSet
    filter_class = filters.DashboardModuleFilter
    serializer = serializers.DashboardModuleSerializer


class UserDashboardModuleEndpoint(ApiEndpoint):

    model = models.UserDashboardModule
    base_viewset = viewsets.UserDashboardModuleViewSet
    serializer = serializers.UserDashboardModuleSerializer


class FormStorageEndpoint(ApiEndpoint):

    model = models.FormStorage
    base_viewset = viewsets.FormStorageViewSet
    serializer = serializers.FormStorageSerializer

    fieldsets = (
        {
            'type': constants.CONTAINER_COLLAPSE,
            'name': _('General'),
            'collapsed': False,
            'fields': (
                    'company', 'status',
                    {'field': 'data', 'read_only': True, 'label': _("Data"), 'type': constants.FIELD_STATIC}
                )
        },
    )

    list_display = (
        {
            'label': _("Form"),
            'field': 'form',
            'type': constants.FIELD_LINK,
            'endpoint': format_lazy(
                '{}{{form.id}}/',
                api_reverse_lazy('core/forms')
            ),
        },
        {
            'label': _('Company'),
            'type': constants.FIELD_LINK,
            'endpoint': format_lazy(
                '{}{{company.id}}/',
                api_reverse_lazy('core/companies')
            ),
            'field': 'company',
        },
        'status',
        'created_at'
    )

    list_buttons = []


class BaseFormFieldEndpoint(ApiEndpoint):

    filter_class = filters.FormFieldFilter
    list_display = ('id', 'group', 'name', 'label', 'placeholder', 'class_name', 'required', 'position', 'help_text',
                    'field_type')

    def get_fieldsets(self):
        return self.model.get_serializer_fields()


class CheckBoxFormFieldEndpoint(BaseFormFieldEndpoint):

    model = models.CheckBoxFormField
    serializer = serializers.CheckBoxFormFieldSerializer


class ImageFormFieldEndpoint(BaseFormFieldEndpoint):

    model = models.ImageFormField
    serializer = serializers.ImageFormFieldSerializer


class RadioButtonsFormFieldEndpoint(BaseFormFieldEndpoint):

    model = models.RadioButtonsFormField
    serializer = serializers.RadioButtonsFormFieldSerializer
    list_display = BaseFormFieldEndpoint.list_display + ('choices',)


class TextAreaFormFieldEndpoint(BaseFormFieldEndpoint):

    model = models.TextAreaFormField
    serializer = serializers.TextAreaFormFieldSerializer
    list_display = BaseFormFieldEndpoint.list_display + ('max_length', 'rows')


class TextFormFieldEndpoint(BaseFormFieldEndpoint):

    model = models.TextFormField
    serializer = serializers.TextFormFieldSerializer
    list_display = BaseFormFieldEndpoint.list_display + ('max_length', 'subtype')


class SelectFormFieldEndpoint(BaseFormFieldEndpoint):

    model = models.SelectFormField
    list_display = BaseFormFieldEndpoint.list_display + ('is_multiple', 'choices')
    serializer = serializers.SelectFormFieldSerializer


class DateFormFieldEndpoint(BaseFormFieldEndpoint):

    model = models.DateFormField
    serializer = serializers.DateFormFieldSerializer


class NumberFormFieldEndpoint(BaseFormFieldEndpoint):

    model = models.NumberFormField
    serializer = serializers.NumberFormFieldSerializer
    list_display = BaseFormFieldEndpoint.list_display + ('min_value', 'max_value', 'step')


class ModelFormFieldEndpoint(BaseFormFieldEndpoint):

    model = models.ModelFormField
    serializer = serializers.ModelFormFieldSerializer


class FileFormFieldEndpoint(BaseFormFieldEndpoint):

    model = models.FileFormField
    serializer = serializers.FileFormFieldSerializer


class FormFieldGroupEndpoint(ApiEndpoint):

    model = models.FormFieldGroup
    base_serializer = serializers.FormFieldGroupSerializer

    fieldsets = (
        'id', 'form', 'name', 'position',
        {
            'field': 'field_list',
            'type': constants.FIELD_RELATED,
            'endpoint': api_reverse_lazy('core/formfields'),
            'many': True
        }
    )

    list_display = (
        'form', 'name', 'position'
    )


class FormEndpoint(ApiEndpoint):
    model = models.Form
    base_viewset = viewsets.FormViewSet

    fieldsets = (
        'id', 'title', {
            'type': constants.FIELD_RELATED,
            'field': 'company',
        },
        'builder', 'is_active', 'short_description', 'save_button_text', 'submit_message',
        {
            'field': 'groups',
            'type': constants.FIELD_RELATED,
            'endpoint': api_reverse_lazy('core/formfieldgroups'),
            'many': True
        }
    )

    list_display = (
        'id', 'title', 'company', 'builder', 'is_active'
    )


class FormBuilderEndpoint(ApiEndpoint):

    model = models.FormBuilder
    base_viewset = viewsets.FormBuilderViewSet


class ContentTypeEndpoint(ApiEndpoint):

    model = ContentType
    base_viewset = viewsets.ContentTypeViewSet
    search_fields = ('model', )


class CountryEndpoint(ApiEndpoint):

    model = models.Country
    base_viewset = viewsets.CitiesLightViewSet
    search_fields = ('name', 'alternate_names')
    filter_fields = ('code2',)


class RegionEndpoint(ApiEndpoint):

    model = models.Region
    base_viewset = viewsets.CitiesLightViewSet
    filter_class = filters.RegionFilter
    search_fields = ('name', 'alternate_names')
    filter_fields = ('country',)


class CityEndpoint(ApiEndpoint):

    model = models.City
    base_viewset = viewsets.CitiesLightViewSet
    search_fields = ('name', 'alternate_names')
    filter_fields = ('country', 'region')


class InvoiceLineEndpoint(ApiEndpoint):

    model = models.InvoiceLine
    serializer = serializers.InvoiceLineSerializer

    fieldsets = ('invoice', 'date', 'units', 'notes', 'unit_price', 'amount', 'unit_type', 'vat')

    list_editable = (
        'date', 'units', 'notes', 'timesheet.job_offer.candidate_contact', 'unit_price', 'amount', {
            'type': constants.FIELD_TEXT,
            'field': 'vat.name',
            'label': _('Code'),
        }, {
            'type': constants.FIELD_LINK,
            'label': _('Timesheets'),
            'field': 'timesheet',
            'text': _('Timesheet'),
            'endpoint': format_lazy('{}{{timesheet.id}}', api_reverse_lazy('hr/timesheets'))
        }, {
            'label': _('Actions'),
            'delim': ' ',
            'fields': ({
                **constants.BUTTON_EDIT,
                'endpoint': format_lazy('{}{{id}}', api_reverse_lazy('core/invoicelines'))
            }, constants.BUTTON_DELETE)
        },
    )

    filter_fields = ('invoice', )


class InvoiceRuleEndpoint(ApiEndpoint):

    model = models.InvoiceRule
    serializer = serializers.InvoiceRuleSerializer

    list_editable = (
        'separation_rule', 'show_candidate_name', 'notice', 'serial_number', 'period', 'period_zero_reference',
        'starting_number', 'comment',
    )

    list_filter = ('company', )


class NoteEndpoint(ApiEndpoint):

    model = models.Note
    serializer = serializers.NoteSerializer

    list_editable = (
        'note',
        {
            'label': _('Created'),
            'fields': ('created_at', 'created_by')
        }, {
            'label': _('Updated'),
            'fields': ('updated_at', 'updated_by')
        }, {
            **constants.BUTTON_EDIT,
            'endpoint': format_lazy('{}{{id}}', api_reverse_lazy('core/notes'))
        }, constants.BUTTON_DELETE,
    )

    fieldsets = (
        'content_type',
        {
            'type': constants.FIELD_TEXT,
            'field': 'object_id',
            'hide': True,
        }, {
            'type': constants.FIELD_TEXTAREA,
            'field': 'note',
        }
    )

    filter_fields = ('object_id', )


class ContactUnavailabilityEndpoint(ApiEndpoint):

    model = models.ContactUnavailability

    list_editable = (
        'unavailable_from', 'unavailable_until', 'notes', 'created_at', 'updated_at', {
            **constants.BUTTON_EDIT,
            'endpoint': format_lazy('{}{{id}}', api_reverse_lazy('core/contactunavailabilities'))
        }, constants.BUTTON_DELETE,
    )

    list_filter = ('contact', )


class BankAccountEndpoint(ApiEndpoint):

    model = models.BankAccount

    fieldsets = ('bank_name', 'bank_account_name', 'bsb', 'account_number')
    search_fields = ('bank_name', 'bank_account_name')


class UserEndpoint(ApiEndpoint):

    model = models.User

    serializer_fields = (
        'id', 'date_joined', {
            'contact': ('id', 'email', 'phone_mobile'),
        }
    )

    list_display = (
        'contact', 'contact.email', 'contact.phone_mobile', 'date_joined',
        {
            'label': _('Login as'),
            'type': constants.FIELD_BUTTON,
            'action': constants.DEFAULT_ACTION_POST,
            'field': 'id',
            'text': _('Login'),
            'redirect': '/',
            'endpoint': format_lazy('{}{{id}}/loginas/', api_reverse_lazy('auth'))
        }
    )

    _fieldset = (
        {
            'field': 'date_joined',
            'type': constants.FIELD_DATETIME,
            'read_only': True,
        },
    )
    fieldsets = {
        'default': (
            {
                'field': 'contact',
                'type': constants.FIELD_RELATED,
                'read_only': True,
            },
        ) + _fieldset + (
            {
                'query': {
                    'user': '{id}',
                },
                'type': constants.FIELD_LIST,
                'label': _('Global Permissions'),
                'endpoint': api_reverse_lazy('company-settings/globalpermissions'),
                'prefilled': {
                    'user': '{id}',
                },
            },
        ),
        'contact': _fieldset
    }

    search_fields = ('contact__first_name', 'contact__last_name', 'contact__email', 'contact__phone_mobile')


class AddressEndpoint(ApiEndpoint):

    model = models.Address
    serializer = serializers.AddressSerializer
    base_viewset = viewsets.AddressViewset

    fieldsets_add = ('street_address',)

    fieldsets = (
        {
            'field': 'street_address',
            'type': constants.FIELD_TEXT,
        }, {
            'field': 'city',
            'read_only': True,
            'type': constants.FIELD_RELATED,
        }, {
            'field': 'postal_code',
            'read_only': True,
            'type': constants.FIELD_TEXT,
        }, {
            'field': 'state',
            'read_only': True,
            'type': constants.FIELD_RELATED,
        }, {
            'field': 'country',
            'read_only': True,
            'type': constants.FIELD_RELATED,
        }, {
            'field': 'latitude',
            'read_only': True,
            'type': constants.FIELD_TEXT,
        }, {
            'field': 'longitude',
            'read_only': True,
            'type': constants.FIELD_TEXT,
        }, {
            'field': 'created_at',
            'read_only': True,
            'type': constants.FIELD_DATETIME,
        }, {
            'field': 'updated_at',
            'read_only': True,
            'type': constants.FIELD_DATETIME,
        },
    )


router.register(endpoint=DashboardModuleEndpoint())
router.register(endpoint=UserDashboardModuleEndpoint())
router.register(endpoint=AddressEndpoint())
router.register(endpoint=BankAccountEndpoint())
router.register(endpoint=CityEndpoint())
router.register(endpoint=CompanyEndpoint())
router.register(endpoint=CompanyAddressEndpoint())
router.register(endpoint=CompanyContactEndpoint())
router.register(endpoint=CompanyContactRelationEndpoint())
router.register(endpoint=CompanyLocalizationEndpoint())
router.register(endpoint=CompanyRelEndpoint())
router.register(models.CompanyTradeReference)
router.register(endpoint=ContactEndpoint())
router.register(endpoint=ContactUnavailabilityEndpoint())
router.register(endpoint=CountryEndpoint())
router.register(models.FileStorage)
router.register(models.Invoice, filter_fields=['customer_company'])
router.register(endpoint=InvoiceLineEndpoint())
router.register(endpoint=NavigationEndpoint())
router.register(endpoint=NoteEndpoint())
router.register(models.Order, filter_fields=('provider_company',))
router.register(endpoint=RegionEndpoint())
router.register(models.Tag, search_fields=('name',))
router.register(endpoint=SiteEndpoint())
router.register(endpoint=WorkflowNodeEndpoint())
router.register(endpoint=WorkflowEndpoint())
router.register(endpoint=WorkflowObjectEndpoint())
router.register(endpoint=FormBuilderEndpoint())
router.register(models.FormField, serializer=serializers.FormFieldSerializer)
router.register(endpoint=FormFieldGroupEndpoint())
router.register(endpoint=FormEndpoint())
router.register(endpoint=FormStorageEndpoint())
router.register(endpoint=ImageFormFieldEndpoint())
router.register(endpoint=TextAreaFormFieldEndpoint())
router.register(endpoint=RadioButtonsFormFieldEndpoint())
router.register(endpoint=TextFormFieldEndpoint())
router.register(endpoint=SelectFormFieldEndpoint())
router.register(endpoint=DateFormFieldEndpoint())
router.register(endpoint=NumberFormFieldEndpoint())
router.register(endpoint=ModelFormFieldEndpoint())
router.register(endpoint=FileFormFieldEndpoint())
router.register(endpoint=CheckBoxFormFieldEndpoint())
router.register(endpoint=ContentTypeEndpoint())
router.register(endpoint=InvoiceRuleEndpoint())
router.register(endpoint=UserEndpoint())
