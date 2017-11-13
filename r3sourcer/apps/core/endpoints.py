from functools import partial

from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.utils.functional import lazy
from django.utils.translation import ugettext_lazy as _
from drf_auto_endpoint.router import router
from drf_auto_endpoint.decorators import bulk_action
from rest_framework.response import Response
from rest_framework.exceptions import ParseError

from . import models
from .api import serializers, viewsets, filters
from .api.endpoints import ApiEndpoint
from .utils.text import format_lazy

from r3sourcer.apps.core_adapter import constants
from r3sourcer.apps.core_adapter.utils import api_reverse_lazy


class ContactEndpoint(ApiEndpoint):
    model = models.Contact
    base_viewset = viewsets.ContactViewset
    serializer = serializers.ContactSerializer
    search_fields = (
        'title',
        'first_name',
        'last_name',
        'address__city__search_names',
        'email',
        'phone_mobile',
        'address__phone_landline',
        'address__phone_fax',
    )

    list_display = (
        {
            'field': 'job_title',
            'type': constants.FIELD_TEXT
        },
        {
            'field': 'picture',
            'type': constants.FIELD_PICTURE,
        },
        'title', 'first_name', 'last_name', 'address.state', 'address.city',
        {
            'field': 'email',
            'link': 'mailto:{field}',
            'type': constants.FIELD_LINK,
        },
        {
            'label': _('Phone'),
            'fields': ({
                'type': constants.FIELD_LINK,
                'link': 'tel:{field}',
                'field': 'phone_mobile',
            }, {
                'type': constants.FIELD_LINK,
                'link': 'tel:{field}',
                'field': 'address.phone_landline',
            }, {
                'type': constants.FIELD_LINK,
                'link': 'tel:{field}',
                'field': 'address.phone_fax',
            },),
        },
        {
            'field': 'availability',
            'type': constants.FIELD_ICON
        },
        {
            'field': 'is_candidate_contact',
            'type': constants.FIELD_ICON
        },
        {
            'field': 'is_company_contact',
            'type': constants.FIELD_ICON
        }
    )

    fieldsets = (
        {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': False,
            'name': _('Picture'),
            'fields': (
                {
                    'type': constants.FIELD_PICTURE,
                    'field': 'picture',
                    'read_only': True
                },
            ),
        },
        {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': False,
            'name': _('Name'),
            'fields': (
                'title', 'first_name', 'last_name'
            ),
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('User relation'),
            'fields': (
                {
                    'type': constants.FIELD_RELATED,
                    'field': 'company_contact',
                    'edit': True,
                    'delete': True,
                    'create': True,
                    'list': True
                },
            )
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Contact information'),
            'fields': (
                'email', 'phone_mobile', 'address.phone_landline', 'address.phone_fax',
                {
                    'type': constants.FIELD_RELATED,
                    'field': 'address',
                    'edit': True,
                    'delete': True,
                    'create': True
                }
            )
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Personal information'),
            'fields': (
                'gender', 'birthday', 'marital_status', 'spouse_name',
                'children'
            )
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Misc'),
            'fields': (
                'is_available', 'phone_mobile_verified', 'email_verified'
            )
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Other'),
            'fields': (
                {
                    'type': constants.FIELD_RELATED,
                    'delete': True,
                    'list': True,
                    'many': True,
                    'create': True,
                    'edit': True,
                    'field': 'company_contact',
                },
            )
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Notes'),
            'fields': (
                {
                    'type': constants.FIELD_RELATED,
                    'delete': True,
                    'list': True,
                    'many': True,
                    'create': True,
                    'edit': True,
                    'field': 'notes',
                },
            )
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Contact unavailabilitie\'s'),
            'fields': (
                {
                    'type': constants.FIELD_RELATED,
                    'delete': True,
                    'list': True,
                    'many': True,
                    'create': True,
                    'edit': True,
                    'field': 'contact_unavailabilities',
                },
            )
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Company contact'),
            'fields': (
                {
                    'type': constants.FIELD_RELATED,
                    'delete': True,
                    'list': True,
                    'many': True,
                    'create': True,
                    'edit': True,
                    'field': 'company_contact',
                },
            )
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': False,
            'name': _('Candidate contact'),
            'fields': (
                {
                    'type': constants.FIELD_STATIC,
                    'field': 'candidate_contacts.residency',
                },
                {
                    'type': constants.FIELD_STATIC,
                    'field': 'candidate_contacts.nationality',
                },
                {
                    'type': constants.FIELD_STATIC,
                    'field': 'candidate_contacts.visa_type',
                },
                {
                    'type': constants.FIELD_STATIC,
                    'field': 'candidate_contacts.visa_expiry_date',
                },
                {
                    'type': constants.FIELD_STATIC,
                    'field': 'candidate_contacts.vevo_checked_at',
                },
                {
                    'type': constants.FIELD_STATIC,
                    'field': 'candidate_contacts.weight',
                },
                {
                    'type': constants.FIELD_STATIC,
                    'field': 'candidate_contacts.height',
                },
                {
                    'type': constants.FIELD_STATIC,
                    'field': 'candidate_contacts.strength',
                },
                {
                    'type': constants.FIELD_STATIC,
                    'field': 'candidate_contacts.language',
                },
                {
                    'type': constants.FIELD_STATIC,
                    'field': 'candidate_contacts.total_score',
                },
                {
                    'type': constants.FIELD_STATIC,
                    'field': 'candidate_contacts.loyalty_score',
                },
                {
                    'type': constants.FIELD_STATIC,
                    'field': 'candidate_contacts.reliability_score',
                },
            ),
        }, {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': False,
            'name': _('Picture'),
            'fields': (
                {
                    'type': constants.FIELD_PICTURE,
                    'field': 'picture',
                    'label_upload': _('Choose a file'),
                    'label_photo': _('Take a photo'),
                },
            ),
        },
        {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': False,
            'name': _('History'),
            'fields': (
                {
                    'type': constants.CONTAINER_COLLAPSE,
                    'collapsed': True,
                    'name': _('History'),
                    'fields': (
                        {
                            'type': constants.FIELD_RELATED,
                            'field': 'object_history',
                            'many': True,
                            'list': True,
                            'readonly': True,
                            'endpoint': api_reverse_lazy('log')
                        },
                    )
                }
            ),
        }
    )

    list_filter = [{
        'field': 'address.state',
        'value': 'name',
    }, 'is_available']


class CompanyAddressEndpoint(ApiEndpoint):

    model = models.CompanyAddress
    base_viewset = viewsets.CompanyAddressViewset
    base_serializer = serializers.CompanyAddressSerializer
    filter_class = filters.CompanyAddressFilter
    fields = (
        '__all__',
        {
            'company': (
                'id', 'name', 'credit_check', 'get_terms_of_payment',
                'approved_credit_limit', 'type',
            ),
            'address': ('__all__', ),
            'primary_contact': ({
                'contact': ('__str__', 'phone_mobile')
            },)
        }
    )
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
                'action': 'openList',
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
                'action': 'openList',
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
                'type': constants.FIELD_LINK,
                'link': 'tel:{field}',
                'field': 'address.phone_landline',
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
                'action': 'sendSMS',
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
            'field': 'state',
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
                'action': 'openList',
                'field': 'id',
            },),
        }
    )

    fieldsets = (
        'name', 'company', 'address', 'hq', 'termination_date',
        'primary_contact', 'active'
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
            'field': 'state',
            'choices': lazy(states_part, list)(),
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

    fields = (
        '__all__',
    )

    list_display = (
        {
            'label': _('Company Name'),
            'type': constants.FIELD_LINK,
            'endpoint': format_lazy(
                '{}{{id}}/',
                api_reverse_lazy('core/companies')
            ),
            'field': 'name',
        },
        {
            'label': _('Primary Contact'),
            'type': constants.FIELD_STATIC,
            'field': 'primary_contact',
        },
        {
            'label': _('Manager'),
            'type': constants.FIELD_STATIC,
            'field': 'manager.__str__',
        },
        {
            'label': _('Available'),
            'read_only': True,
            'field': 'available',
        },
        {
            'label': _('Credit Info'),
            'fields': ({
                'type': constants.FIELD_STATIC,
                'field': 'credit_check',
            }, {
                'type': constants.FIELD_DATE,
                'field': 'credit_check_date',
            }, {
                'type': constants.FIELD_STATIC,
                'field': 'approved_credit_limit',
            }, {
                'type': constants.FIELD_STATIC,
                'field': 'terms_of_pay',
            }),
        },
        {
            'label': _('Client State'),
            'field': 'state',
        },
    )

    fieldsets = (
        {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': False,
            'name': _('Picture'),
            'fields': (
                {
                    'type': constants.FIELD_PICTURE,
                    'field': 'logo',
                    'label_upload': _('Choose a file'),
                    'label_photo': _('Take a photo'),
                },
            ),
        },
        {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': False,
            'name': _('General'),
            'fields': (
                'name', 'business_id', 'registered_for_gst', 'tax_number',
                {
                    'label': _('Primary Contact'),
                    'type': constants.FIELD_STATIC,
                    'field': 'primary_contact',
                },
                {
                    'label': _('Primary Contact'),
                    'type': constants.FIELD_STATIC,
                    'field': 'manager',
                },
                'website', 'type', 'company_rating',
                {
                    'label': _('Date of incorporation'),
                    'type': constants.FIELD_DATE,
                    'field': 'date_of_incorporation'
                },
            ),
        },
        {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Company Address'),
            'fields': (
                {
                    'label': _('Addresses'),
                    'type': constants.FIELD_RELATED,
                    'list': True,
                    'edit': True,
                    'field': 'company_addresses',
                    'endpoint': api_reverse_lazy('core/notes'),
                },
                {
                    'label': _('HQ Address'),
                    'type': constants.CONTAINER_COLLAPSE,
                    'collapsed': False,
                    'fields': (
                        'get_hq_address.address.__str__', 'get_hq_address.hq',
                        'get_hq_address.name',
                        {
                            'label': _('Termination date'),
                            'type': constants.FIELD_DATE,
                            'field': 'get_hq_address.termination_date'
                        }, 'get_hq_address.primary_contact.__str__',
                        'get_hq_address.active', 'get_hq_address.created',
                        'get_hq_address.updated',
                    )
                },

            )
        },
        {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Company contacts'),
            'fields': ()
        },
        {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Jobsites'),
            'fields': (
                {
                    'label': _('Jobsites'),
                    'type': constants.FIELD_RELATED,
                    'list': True,
                    'edit': True,
                    'field': 'jobsites',
                    'endpoint': api_reverse_lazy('core/jobsites'),
                },
            )
        },
        {
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
        },
        {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Banking details'),
            'fields': (
                'billing_email',
                {
                    'type': constants.FIELD_RELATED,
                    'field': 'bank_account',
                    'endpoint': api_reverse_lazy('core/bankaccounts'),
                },
                'expense_account'
            )
        },
        {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Price list'),
            'fields': (
                {
                    'label': _('Price list'),
                    'type': constants.FIELD_RELATED,
                    'list': True,
                    'edit': True,
                    'field': 'price_lists',
                    'endpoint': api_reverse_lazy('core/pricelists'),
                },
            )
        },
        {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Company state timeline'),
            'fields': (
                {
                    'type': constants.FIELD_TIMELINE,
                    'label': _('States Timeline'),
                    'field': 'id',
                    'endpoint': format_lazy(
                        '{}timeline/',
                        api_reverse_lazy('core/workflownodes'),
                    ),
                    'query': ['model', 'object_id'],
                    'model': 'core.company',
                    'object_id': '{id}',
                },
            )
        },
        {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Notes'),
            'fields': (
                'description',
                {
                    'label': _('Notes'),
                    'type': constants.FIELD_RELATED,
                    'list': True,
                    'edit': True,
                    'field': 'notes',
                    'endpoint': api_reverse_lazy('core/notes'),
                },
            )
        },
        {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Other'),
            'fields': (
                {
                    'label': _('Master company'),
                    'type': constants.FIELD_RELATED,
                    'list': True,
                    'readonly': True,
                    'field': 'get_master_company',
                    'endpoint': api_reverse_lazy('core/companies'),
                },
                {
                    'label': _('Portfolio manager'),
                    'type': constants.FIELD_RELATED,
                    'field': 'manager',
                    'endpoint': '',
                }, 'timesheet_approval_scheme',
                {
                    'label': _('Parent'),
                    'type': constants.FIELD_RELATED,
                    'field': 'parent.__str__',
                    'endpoint': api_reverse_lazy('core/companies'),
                },
                {
                    'label': _('Created date'),
                    'type': constants.FIELD_DATETIME,
                    'field': 'created',
                },
                {
                    'label': _('Updated date'),
                    'type': constants.FIELD_DATETIME,
                    'field': 'updated',
                },
            )
        },
        {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('Logo'),
            'fields': (
                {
                    'type': constants.FIELD_PICTURE,
                    'field': 'logo',
                    'label_upload': _('Choose a file'),
                    'label_photo': _('Take a photo'),
                },
            ),
        },
        {
            'type': constants.CONTAINER_COLLAPSE,
            'collapsed': True,
            'name': _('History'),
            'fields': (
                {
                    'type': constants.FIELD_RELATED,
                    'field': 'object_history',
                    'many': True,
                    'list': True,
                    'readonly': True,
                    'endpoint': api_reverse_lazy('log')
                },
            )
        }
    )


class CompanyContactEndpoint(ApiEndpoint):

    model = models.CompanyContact
    base_viewset = viewsets.CompanyContactViewset
    serializer = serializers.CompanyContactRenderSerializer
    filter_class = filters.CompanyContactFilter

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
                    'action': 'sendSMS',
                    'text': _('SMS'),
                    'icon': 'fa-commenting',
                    'fields': ('contact.phone_mobile',)
                }
            ),
        },
        'contact.email',
        'receive_order_confirmation_sms'
    )

    fieldsets = (
        'contact', 'job_title', 'rating_unreliable',
        'receive_order_confirmation_sms',
        'voip_username', 'voip_password', 'pin_code'
    )

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
        },]

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
            'query': ['model', 'object_id'],
            'model': 'core.companyrel',
            'object_id': '{id}',
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
    fieldsets = ('name', 'model', )


class WorkflowNodeEndpoint(ApiEndpoint):

    model = models.WorkflowNode
    base_viewset = viewsets.WorkflowNodeViewset
    serializer = serializers.WorkflowNodeSerializer
    filter_class = filters.WorkflowNodeFilter

    fieldsets = (
        'workflow', 'number', 'name_before_activation',
        'name_after_activation', {
            'type': constants.FIELD_RULE,
            'field': 'rules',
        }, 'company', 'active', 'hardlock',
    )


class WorkflowObjectEndpoint(ApiEndpoint):

    model = models.WorkflowObject
    serializer = serializers.WorkflowObjectSerializer

    fieldsets = ({
        'type': constants.CONTAINER_HIDDEN,
        'name': _('Residency'),
        'fields': [
            'object_id'
        ],
    }, 'state', {
        'type': constants.FIELD_TEXTAREA,
        'field': 'comment'
    }, 'active')

    list_filter = ('object_id', 'active', 'state.workflow.name')


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
        'id', 'title', 'company', 'builder', 'is_active', 'short_description',
        'save_button_text', 'submit_message',
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


router.register(endpoint=DashboardModuleEndpoint())
router.register(endpoint=UserDashboardModuleEndpoint())
router.register(models.Address, serializer=serializers.AddressSerializer)
router.register(models.BankAccount)
router.register(models.City, filter_fields=('country', 'region'))
router.register(endpoint=CompanyEndpoint())
router.register(endpoint=CompanyAddressEndpoint())
router.register(endpoint=CompanyContactEndpoint())
router.register(models.CompanyContactRelationship,
                serializer=serializers.CompanyContactRelationshipSerializer)
router.register(endpoint=CompanyLocalizationEndpoint())
router.register(endpoint=CompanyRelEndpoint())
router.register(models.CompanyTradeReference)
router.register(endpoint=ContactEndpoint())
router.register(models.ContactUnavailability)
router.register(models.Country)
router.register(models.FileStorage)
router.register(models.Invoice, filter_fields=['customer_company'])
router.register(models.InvoiceLine)
router.register(endpoint=NavigationEndpoint())
router.register(models.Note)
router.register(models.Order, filter_fields=('provider_company',))
router.register(models.Region, filter_fields=('country',))
router.register(models.Tag)
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
