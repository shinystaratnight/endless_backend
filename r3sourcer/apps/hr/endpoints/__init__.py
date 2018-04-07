import datetime

from functools import partial

from django.utils.functional import lazy
from django.utils.translation import ugettext_lazy as _
from drf_auto_endpoint.router import router

from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.core.utils.text import format_lazy
from r3sourcer.apps.core_adapter import constants
from r3sourcer.apps.core_adapter.utils import api_reverse_lazy

from r3sourcer.apps.hr import models as hr_models
from r3sourcer.apps.hr.api import filters as hr_filters, viewsets as hr_viewsets
from r3sourcer.apps.hr.api.serializers import job as job_serializers
from r3sourcer.apps.hr.endpoints.payment import InvoiceEndpoint
from r3sourcer.apps.hr.endpoints.timesheet_endpoint import TimeSheetEndpoint, ExtranetCandidateTimesheetEndpoint


class JobsiteEndpoint(ApiEndpoint):
    model = hr_models.Jobsite
    filter_class = hr_filters.JobsiteFilter
    serializer = job_serializers.JobsiteSerializer

    search_fields = ('address__city__search_names', 'address__street_address', 'master_company__name')

    list_display = (
        {
            'type': constants.FIELD_STATIC,
            'label': _('Site Name'),
            'fields': ('__str__', ),
        }, {
            'type': constants.FIELD_TEXT,
            'label': _('State'),
            'field': 'address.state.name',
        }, {
            'type': constants.FIELD_TEXT,
            'label': _('City'),
            'field': 'address.city.name',
        },
        'regular_company', 'portfolio_manager', 'industry', 'start_date',
        'end_date', 'active_states'
    )

    fieldsets = (
        {
            'type': constants.CONTAINER_ROW,
            'label': '{__str__}',
            'fields': ({
                'type': constants.CONTAINER_COLUMN,
                'fields': (
                    'industry',
                    {
                        'type': constants.FIELD_TEXT,
                        'label': _('Site Name'),
                        'field': 'short_name',
                        'help': '',
                    },
                    'regular_company', 'primary_contact', 'portfolio_manager', 'address',
                    {
                        'field': 'master_company.id',
                        'type': constants.FIELD_TEXT,
                        'hidden': True,
                    }
                ),
            }, )
        }, {
            'type': constants.CONTAINER_ROW,
            'label': 'Timeframe',
            'fields': ({
                'type': constants.CONTAINER_COLUMN,
                'fields': ('start_date', 'end_date', 'is_available',),
            }, ),
        }, {
            'type': constants.FIELD_LIST,
            'field': 'id_',
            'query': {
                'jobsite': '{id}',
            },
            'label': _('Jobs'),
            'add_label': _('Add'),
            'endpoint': api_reverse_lazy('hr/jobs'),
            'prefilled': {
                'jobsite': '{id}',
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
                        'model': 'hr.jobsite',
                        'object_id': '{id}',
                    },
                },
            )
        }, {
            'type': constants.FIELD_LIST,
            'query': {
                'object_id': '{id}'
            },
            'collapsed': True,
            'label': _('States History'),
            'add_label': _('Add'),
            'endpoint': api_reverse_lazy('core/workflowobjects'),
            'prefilled': {
                'object_id': '{id}',
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
        },
    )

    list_editable = (
        '__str__', 'primary_contact', 'start_date', 'end_date', 'notes',
    )

    def get_list_filter(self):
        states_part = partial(
            core_models.WorkflowNode.get_model_all_states, hr_models.Jobsite
        )
        au_regions = partial(core_models.Region.get_countrys_regions, 'AU')
        list_filter = [
            'industry', {
                'type': constants.FIELD_SELECT,
                'field': 'state',
                'label': _('State'),
                'choices': lazy(au_regions, list),
            }, {
                'label': _('Client'),
                'field': 'regular_company',
            },
            'portfolio_manager',
            {
                'type': constants.FIELD_SELECT,
                'field': 'active_states',
                'choices': lazy(states_part, list),
            },
        ]

        return list_filter


class FavouriteListEndpoint(ApiEndpoint):

    model = hr_models.FavouriteList
    serializer_fields = [
        '__all__',
        {
            'company': ['id', 'name', 'manager'],
        }
    ]
    fieldsets = ('candidate_contact', 'company_contact', 'company', 'jobsite', 'job')
    list_display = (
        'company_contact', 'candidate_contact', {
            'field': 'company.manager',
            'label': _('Company Manager'),
        }, 'company', 'jobsite', 'job',
    )
    list_editable = {
        'default': (
            'company_contact', {
                'field': 'company.manager',
                'label': _('Company Manager'),
            }, 'company', 'jobsite', 'job',
        ),
        'job': (
            'company_contact', 'candidate_contact', 'job', {
                'label': _('Actions'),
                'delim': ' ',
                'fields': (constants.BUTTON_DELETE,)
            },
        )
    }
    list_filter = [
        'company_contact', 'candidate_contact', 'company', 'jobsite', 'job'
    ]


class JobOfferEndpoint(ApiEndpoint):
    model = hr_models.JobOffer
    base_viewset = hr_viewsets.JobOfferViewset
    serializer = job_serializers.JobOfferSerializer
    filter_class = hr_filters.JobOfferFilter

    list_display = ('shift.date.shift_date', 'status')
    list_editable = (
        'candidate_contact', 'shift.date.shift_date', 'shift.time',
        {
            'label': _('Status'),
            'delim': ' ',
            'fields': [{
                'field': 'status',
                'type': constants.FIELD_ICON,
                'values': {
                    0: 'minus-circle',
                    1: 'check-circle',
                    2: 'times-circle',
                },
            }, {
                'type': constants.FIELD_SELECT,
                'field': 'status',
            }]
        }, {
            'label': _('SMS History'),
            'delim': ' ',
            'fields': [{
                'type': constants.FIELD_BUTTON,
                'text': _('Offer'),
                'field': 'offer_sent_by_sms.id',
                'action': constants.DEFAULT_ACTION_EDIT,
                'endpoint': format_lazy('{}{{field}}', api_reverse_lazy('sms-interface/smsmessages')),
            }, {
                'type': constants.FIELD_BUTTON,
                'text': _('Reply'),
                'field': 'reply_received_by_sms.id',
                'action': constants.DEFAULT_ACTION_EDIT,
                'endpoint': format_lazy('{}{{field}}', api_reverse_lazy('sms-interface/smsmessages')),
            }],
        }, {
            'label': _('Client/Candidate Rate'),
            'delim': ' / ',
            'fields': ({
                'field': 'client_rate',
                'type': constants.FIELD_STATIC,
                'display': '${field}/h',
            }, {
                'field': 'candidate_rate',
                'type': constants.FIELD_STATIC,
                'display': '${field}/h',
            })
        }, {
            'type': constants.FIELD_LINK,
            'label': _('Timesheets'),
            'field': 'timesheets',
            'text': _('Link to TimeSheet'),
            'endpoint': format_lazy('{}{{field}}', api_reverse_lazy('hr/timesheets'))
        }, {
            'label': _('Actions'),
            'delim': ' ',
            'fields': ({
                'type': constants.FIELD_BUTTON,
                'icon': 'fa-check-circle',
                'field': 'has_accept_action',
                'action': constants.DEFAULT_ACTION_POST,
                'endpoint': format_lazy('{}{{id}}/accept', api_reverse_lazy('hr/joboffers')),
                'text_color': '#5cb85c',
                'title': _('Accept'),
            }, {
                'type': constants.FIELD_BUTTON,
                'icon': 'fa-minus-circle',
                'field': 'has_cancel_action',
                'action': constants.DEFAULT_ACTION_POST,
                'endpoint': format_lazy('{}{{id}}/cancel', api_reverse_lazy('hr/joboffers')),
                'text_color': '#f32700',
                'title': _('Cancel'),
            }, {
                'type': constants.FIELD_BUTTON,
                'icon': 'fa-commenting',
                'field': 'has_resend_action',
                'action': constants.DEFAULT_ACTION_POST,
                'endpoint': format_lazy('{}{{id}}/resend', api_reverse_lazy('hr/joboffers')),
                'text_color': '#f0ad4e',
                'title': _('Resend JO'),
            }, constants.BUTTON_DELETE),
        }
    )
    ordering = ('-shift.date.shift_date', )
    list_filter = ['candidate_contact']


class CarrierListEndpoint(ApiEndpoint):
    model = hr_models.CarrierList

    list_display = ('candidate_contact', 'target_date', 'confirmed_available', 'job_offer')
    list_editable = ('target_date', 'confirmed_available', 'job_offer')
    list_filter = ('candidate_contact', )


class BlackListEndpoint(ApiEndpoint):
    model = hr_models.BlackList

    list_display = ('company', 'candidate_contact', 'timesheet', 'jobsite')
    list_editable = ('company', 'timesheet', 'jobsite')
    list_filter = ('candidate_contact', )


class CandidateEvaluationEndpoint(ApiEndpoint):
    model = hr_models.CandidateEvaluation

    list_display = ('candidate_contact', 'supervisor', 'evaluated_at')
    list_editable = (
        'supervisor', 'evaluated_at', 'level_of_communication', 'was_on_time', 'was_motivated', 'had_ppe_and_tickets',
        'met_expectations', 'representation',
        {
            'type': constants.FIELD_LINK,
            'field': 'reference_timesheet',
            'endpoint': format_lazy('{}{{reference_timesheet.id}}', api_reverse_lazy('hr/timesheets')),
        }
    )
    fieldsets = (
        'candidate_contact', 'supervisor', {
            'field': 'evaluated_at',
            'read_only': False,
            'type': constants.FIELD_DATETIME,
        }, 'level_of_communication', 'was_on_time', 'was_motivated',
        'had_ppe_and_tickets', 'met_expectations', 'representation', 'reference_timesheet'
    )
    list_filter = ('candidate_contact', )


class JobEndpoint(ApiEndpoint):
    model = hr_models.Job
    base_viewset = hr_viewsets.JobViewset
    serializer = job_serializers.JobSerializer
    filter_class = hr_filters.JobFilter

    list_display = ('workers', {
        'label': _('Jobsite'),
        'fields': ('jobsite', 'jobsite.primary_contact', {
            'type': constants.FIELD_LINK,
            'link': 'tel:{field}',
            'field': 'jobsite.primary_contact.contact.phone_mobile',
        }),
    }, 'position', {
        'label': _('Fulfilled'),
        'delim': '/',
        'title': _('today / next day'),
        'fields': ({
            'field': 'is_fulfilled_today',
            'type': constants.FIELD_ICON,
            'values': {
                0: 'times-circle',
                1: 'check-circle',
                2: 'exclamation-circle',
                3: 'minus-circle',
            },
            'color': {
                0: 'danger',
                1: 'success',
                2: 'warning',
            },
        }, {
            'field': 'is_fulfilled',
            'type': constants.FIELD_ICON,
            'values': {
                0: 'times-circle',
                1: 'check-circle',
                2: 'exclamation-circle',
                3: 'minus-circle',
            },
            'color': {
                0: 'danger',
                1: 'success',
                2: 'warning',
            },
        }),
    }, {
        'label': _('Actions'),
        'fields': ({
            'type': constants.FIELD_BUTTON,
            'icon': 'fa-times',
            'text': _('Cancel Shift Dates'),
            'action': constants.DEFAULT_ACTION_EDIT,
            'hidden': 'no_sds',
            'field': 'id',
        }, {
            'type': constants.FIELD_BUTTON,
            'icon': 'fa-sign-in',
            'text': _('Fill-in'),
            'action': 'fillin',
            'hidden': 'hide_fillin',
            'field': 'id',
        })
    }, {
        'label': _('State'),
        'fields': ({
            'field': 'active_states',
        },)
    }, {
        'label': _('Title'),
        'fields': ({
            'field': 'title',
        },)
    }, {
        'label': _('Created at'),
        'field': 'created_at',
    }, {
        'label': _('Updated at'),
        'field': 'updated_at',
    }, {
        'label': _('Published'),
        'field': 'published',
    }, {
        'label': _('Publishing Date'),
        'name': 'publish_on',
        'field': 'publish_on',
    }, {
        'label': _('Expiration date'),
        'name': 'expires_on',
        'field': 'expires_on',
    },)

    list_tabs = [{
        'label': _('Details'),
        'is_collapsed': False,
        'fields': ('fulfilled', 'actions', 'timesheets', 'activities', 'state')
    }, {
        'label': _('Other'),
        'fields': ('title', 'created_at', 'updated_at', 'published', 'publish_on', 'expires_on')
    }]

    search_fields = (
        'workers', 'jobsite__address__city__search_names', 'publish_on', 'expires_on',
        'jobsite__address__street_address', 'jobsite__master_company__name', 'position__name'
    )

    fieldsets = ({
        'type': constants.CONTAINER_ROW,
        'label': '{jobsite.__str__} {position.__str__} {work_start_date}',
        'fields': (
            {
                'type': constants.CONTAINER_COLUMN,
                'fields': (
                    {
                        'label': _('Client'),
                        'field': 'customer_company',
                        'type': constants.FIELD_RELATED,
                        'query': {
                            'fields': 'primary_contact',
                        },
                    }, {
                        'label': _('Client representative'),
                        'field': 'customer_representative',
                        'type': constants.FIELD_RELATED,
                        'query': {
                            'jobsites': '{jobsite.id}',
                        },
                        'default': '{jobsite.primary_contact.id}',
                        'read_only': True,
                        'showIf': [
                            'jobsite.id',
                        ]
                    }, {
                        'label': _('Provider company'),
                        'field': 'provider_company',
                        'type': constants.FIELD_RELATED,
                        'query': {
                            'type': 'master',
                            'regular_company': '{customer_company.id}',
                        },
                        'default': '{customer_company.master_company.id}',
                        'read_only': True,
                        'showIf': [
                            'customer_company.id',
                        ]
                    }, {
                        'label': _('Provider representative'),
                        'field': 'provider_representative',
                        'type': constants.FIELD_RELATED,
                        'query': {
                            'customer_company': '{customer_company.id}',
                            'master_company': '{provider_company.id}',
                        },
                        'default': '{customer_company.primary_contact.id}',
                        'read_only': True,
                        'showIf': [
                            'provider_company.id',
                        ]
                    }, {
                        'label': _('Accepted at'),
                        'field': 'provider_signed_at',
                        'type': constants.FIELD_DATETIME,
                        'read_only': True,
                        'showIf': [
                            'provider_signed_at',
                        ]
                    }
                )
            }, {
                'type': constants.CONTAINER_COLUMN,
                'fields': (
                    {
                        'label': _('Jobsite'),
                        'field': 'jobsite',
                        'type': constants.FIELD_RELATED,
                        'query': {
                            'company': '{customer_company.id}',
                            'fields': 'primary_contact',
                        }
                    }, {
                        'label': _('Position'),
                        'field': 'position',
                        'type': constants.FIELD_RELATED,
                        'add': False,
                        'query': {
                            'company': '{customer_company.id}',
                        }
                    }, {
                        'field': 'workers',
                        'type': constants.FIELD_TEXT,
                        'label': _('Number Of workers'),
                    }, {
                        'field': 'work_start_date',
                        'type': constants.FIELD_DATE,
                        'default': datetime.date.today(),
                    },
                    'default_shift_starting_time',
                    {
                        'type': constants.FIELD_RELATED,
                        'label': _('Candidate rate default'),
                        'query': {
                            'skill': '{position.id}',
                        },
                        'field': 'hourly_rate_default',
                        'values': ['hourly_rate'],
                        'display': '${hourly_rate}/h',
                    }, {
                        'type': constants.FIELD_TEXTAREA,
                        'field': 'notes',
                    }
                )
            }
        )
    }, {
        'type': constants.FIELD_LIST,
        'field': 'id_',
        'query': {
            'job': '{id}',
        },
        'label': _('Shift Dates'),
        'add_label': _('Add'),
        'add_endpoint': api_reverse_lazy('hr/shiftdates'),
        'edit_endpoint': format_lazy('{}{{date.id}}', api_reverse_lazy('hr/shiftdates')),
        'endpoint': api_reverse_lazy('hr/shifts'),
        'prefilled': {
            'job': '{id}',
        },
        'metadata_query': {
            'editable_type': 'job',
        },
        'add_metadata_query': {
            'fieldsets_type': 'job',
        },
    }, {
        'type': constants.FIELD_LIST,
        'field': 'id_',
        'query': {
            'job': '{id}',
        },
        'label': _('Job Offers'),
        'add_label': _('Fill in'),
        'add_endpoint': format_lazy('{}{{id}}/fillin/', api_reverse_lazy('hr/jobs')),
        'endpoint': api_reverse_lazy('hr/joboffers'),
        'add_metadata_query': {
            'type': 'list',
        },
    }, {
        'type': constants.CONTAINER_ROW,
        'label': _('Job state timeline'),
        'fields': (
            {
                'type': constants.FIELD_TIMELINE,
                'label': _('States Timeline'),
                'field': 'id',
                'endpoint': format_lazy('{}timeline/', api_reverse_lazy('core/workflownodes')),
                'query': {
                    'model': 'hr.job',
                    'object_id': '{id}',
                }
            },
        )
    }, {
        'type': constants.FIELD_LIST,
        'field': 'id_',
        'query': {
            'company_contact': '{customer_representative.id}',
        },
        'metadata_query': {
            'editable_type': 'job',
        },
        'label': _('Favourite List'),
        'add_label': _('Add'),
        'endpoint': api_reverse_lazy('hr/favouritelists'),
        'prefilled': {
            'company_contact': '{customer_representative.id}',
            'job': '{id}',
        }
    })

    list_editable = (
        '__str__', 'position', 'work_start_date',
        {
            'type': constants.FIELD_TIME,
            'field': 'default_shift_starting_time',
            'label': _('Shift Starting Time'),
        }, {
            'label': _('Fill in'),
            'delim': ' ',
            'fields': ({
                'type': constants.FIELD_BUTTON,
                'icon': 'fa-sign-in',
                'text': _('Fill in'),
                'action': 'fillin',
                'hidden': 'hide_fillin',
                'field': 'id',
            }, )
        }, {
            'label': _('Fulfilled'),
            'delim': '/',
            'title': _('today / next day'),
            'fields': ({
                'field': 'is_fulfilled_today',
                'type': constants.FIELD_ICON,
                'values': {
                    0: 'times-circle',
                    1: 'check-circle',
                    2: 'exclamation-circle',
                    3: 'minus-circle',
                },
                'color': {
                    0: 'danger',
                    1: 'success',
                    2: 'warning',
                },
            }, {
                'field': 'is_fulfilled',
                'type': constants.FIELD_ICON,
                'values': {
                    0: 'times-circle',
                    1: 'check-circle',
                    2: 'exclamation-circle',
                    3: 'minus-circle',
                },
                'color': {
                    0: 'danger',
                    1: 'success',
                    2: 'warning',
                },
            }),
        }, {
            'label': _('State'),
            'fields': ({
                'field': 'active_states',
            },)
        }, {
            'label': _('Actions'),
            'delim': ' ',
            'fields': (
                {
                    **constants.BUTTON_EDIT,
                    'endpoint': format_lazy('{}{{id}}', api_reverse_lazy('hr/jobs'))
                },
                constants.BUTTON_DELETE
            )
        },
    )
    list_editable_buttons = []

    def get_list_filter(self):
        states_part = partial(
            core_models.WorkflowNode.get_model_all_states, hr_models.Job
        )
        list_filter = [{
                'type': constants.FIELD_DATE,
                'label': _('Shift start date'),
                'field': 'shift_dates.shift_date',
                'distinct': True,
            }, 'jobsite', {
                'label': _('Skill'),
                'field': 'position',
            }, 'provider_representative', {
                'type': constants.FIELD_SELECT,
                'field': 'active_states',
                'label': _('State'),
                'choices': lazy(states_part, list),
            }, {
                'type': constants.FIELD_SELECT,
                'field': 'published',
                'choices': [{'label': 'True', 'value': 'True'},
                            {'label': 'False', 'value': 'False'}],
            }, 'customer_company'
        ]

        return list_filter


class ShiftEndpoint(ApiEndpoint):
    model = hr_models.Shift
    serializer = job_serializers.ShiftSerializer
    filter_class = hr_filters.ShiftFilter

    list_displzy = ('workers', 'time')

    fieldsets = ('date', 'time', 'workers', 'hourly_rate')

    _list_editable = (
        {
            'type': constants.FIELD_DATE,
            'label': _('Date'),
            'name': 'date.shift_date',
            'field': 'date.shift_date',
        }, 'workers', {
            'type': constants.FIELD_TEXT,
            'label': _('Candidate rate'),
            'field': 'hourly_rate.hourly_rate',
            'display': '${field}/h',
        }, {
            'type': constants.FIELD_TIME,
            'field': 'time',
            'name': 'time',
            'label': _('Shift start time'),
        }, {
            'type': constants.FIELD_ICON,
            'field': 'is_fulfilled',
            'label': _('Fulfilled'),
            'values': {
                0: 'times-circle',
                1: 'check-circle',
                2: 'exclamation-circle',
                3: 'minus-circle',
            },
        },
    )

    list_editable = {
        'default': _list_editable + (
            {
                'label': _('Actions'),
                'delim': ' ',
                'fields': (constants.BUTTON_DELETE,)
            },
        ),
        'job': _list_editable + (
            {
                'label': _('Actions'),
                'delim': ' ',
                'fields': (
                    {
                        **constants.BUTTON_EDIT,
                        'endpoint': format_lazy('{}{{id}}', api_reverse_lazy('hr/shiftdates')),
                    },
                    constants.BUTTON_DELETE,
                )
            },
        ),
        'shift_date': (
            {
                'type': constants.FIELD_TIME,
                'field': 'time',
                'name': 'time',
                'label': _('Shift start time'),
            }, 'workers', {
                'type': constants.FIELD_TEXT,
                'label': _('Candidate rate'),
                'field': 'hourly_rate.hourly_rate',
                'display': '${field}/h',
            },
        )
    }

    ordering = ('-date.shift_date', '-time')

    search_fields = ('date__job', )

    list_editable_buttons = []


class ShiftDateEndpoint(ApiEndpoint):
    model = hr_models.ShiftDate

    fieldsets = {
        'default': (
            'job', 'shift_date', 'workers', 'hourly_rate',
            {
                'type': constants.FIELD_LIST,
                'field': 'id_',
                'query': {
                    'date': '{id}',
                },
                'metadata_query': {
                    'editable_type': 'shift_date',
                },
                'label': _('Shifts'),
                'add_label': _('Add'),
                'endpoint': api_reverse_lazy('hr/shifts'),
                'prefilled': {
                    'date': '{id}',
                },
                'delay': True,
            },
        ),
        'job': (
            {
                'type': constants.FIELD_RELATED,
                'field': 'job',
                'hide': True,
            }, {
                'type': constants.FIELD_DATE,
                'field': 'shift_date',
            }, {
                'type': constants.FIELD_LIST,
                'field': 'id_',
                'query': {
                    'date': '{id}',
                },
                'metadata_query': {
                    'editable_type': 'shift_date',
                },
                'label': _('Shifts'),
                'add_label': _('Add'),
                'endpoint': api_reverse_lazy('hr/shifts'),
                'prefilled': {
                    'date': '{id}',
                },
                'delay': True,
                'default': {
                    'date__shift_date': '{shift_date}',
                    'job': '{job.id}',
                },
                'unique': ('time', )
            },
        ),
    }


class CandidateJobOfferEndpoint(ApiEndpoint):
    model = hr_models.JobOffer
    serializer = job_serializers.CandidateJobOfferSerializer
    base_viewset = hr_viewsets.JobOffersCandidateViewset

    edit_disabled = True

    list_display = (
        {
            'label': _('Times'),
            'fields': ({
                'type': constants.FIELD_STATIC,
                'text': format_lazy('{{shift.date.shift_date__date}}'),
                'label': _('Shift date'),
                'field': 'shift.date.shift_date',
            }, {
                'type': constants.FIELD_STATIC,
                'label': _('Shift Time'),
                'field': 'shift.time',
            })
        },
        'shift.date.job.position',
        {
            'field': 'shift.date.job.customer_company',
            'type': constants.FIELD_RELATED,
            'label': _('Client'),
        }, {
            'label': _('Job Site - Map'),
            'delim': ' ',
            'fields': (
                {
                    'type': constants.FIELD_RELATED,
                    'field': 'jobsite_address',
                }, {
                    'type': constants.FIELD_BUTTON,
                    'icon': 'fa-map-marker',
                    'text_color': '#006ce5',
                    'title': _('Open Map'),
                    'action': 'openMap',
                    'fields': ('latitude', 'longitude'),
                }
            )
        }, {
            'type': constants.FIELD_RELATED,
            'label': _('Job Site Contact'),
            'field': 'shift.date.job.jobsite.primary_contact',
        }, {
            'label': _('Status'),
            'fields': (
                {
                    'type': constants.FIELD_BUTTON,
                    'icon': 'fa-check-circle',
                    'field': 'hide_buttons',
                    'action': constants.DEFAULT_ACTION_POST,
                    'endpoint': format_lazy('{}{{id}}/accept', api_reverse_lazy('hr/joboffers')),
                    'color': 'success',
                    'text': _('Accept'),
                    'hidden': 'hide_buttons',
                }, {
                    'type': constants.FIELD_BUTTON,
                    'icon': 'fa-times-circle',
                    'field': 'hide_buttons',
                    'action': constants.DEFAULT_ACTION_POST,
                    'endpoint': format_lazy('{}{{id}}/cancel', api_reverse_lazy('hr/joboffers')),
                    'text': _('Decline'),
                    'color': 'danger',
                    'hidden': 'hide_buttons',
                }, {
                    'type': constants.FIELD_ICON,
                    'field': 'status_icon',
                    'showIf': ['hide_buttons'],
                    'values': {
                        True: 'check',
                        False: 'times',
                    },
                }, {
                    'type': constants.FIELD_TEXT,
                    'field': 'status',
                    'showIf': ['hide_buttons'],
                },
            )
        }
    )

    ordering = ('-shift.date.shift_date', '-shift.time')


router.register(endpoint=JobsiteEndpoint())
router.register(hr_models.JobsiteUnavailability)
router.register(endpoint=JobEndpoint())
router.register(endpoint=ShiftDateEndpoint())
router.register(endpoint=ShiftEndpoint())
router.register(endpoint=TimeSheetEndpoint())
router.register(endpoint=ExtranetCandidateTimesheetEndpoint(), url='hr/timesheets-candidate')
router.register(hr_models.TimeSheetIssue)
router.register(endpoint=JobOfferEndpoint())
router.register(endpoint=CandidateEvaluationEndpoint())
router.register(endpoint=BlackListEndpoint())
router.register(endpoint=FavouriteListEndpoint())
router.register(endpoint=CarrierListEndpoint())
router.register(hr_models.Payslip)
router.register(hr_models.PayslipLine)
router.register(hr_models.PayslipRule)
router.register(endpoint=InvoiceEndpoint(), replace=True)
router.register(endpoint=CandidateJobOfferEndpoint(), url='hr/joboffers-candidate')
