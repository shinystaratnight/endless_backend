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
from r3sourcer.apps.hr.api.serializers import vacancy as vacancy_serializers
from r3sourcer.apps.hr.endpoints.payment import InvoiceEndpoint
from r3sourcer.apps.hr.endpoints.timesheet_endpoint import TimeSheetEndpoint, ExtranetCandidateTimesheetEndpoint


class JobsiteEndpoint(ApiEndpoint):
    model = hr_models.Jobsite
    filter_class = hr_filters.JobsiteFilter

    search_fields = (
        'jobsite_addresses__address__city__search_names', 'jobsite_addresses__address__street_address',
        'master_company__name'
    )

    fieldsets = (
        'industry', 'master_company', 'portfolio_manager', 'primary_contact', 'is_available', 'notes', 'start_date',
        'end_date',
    )

    list_editable = (
        '__str__', 'primary_contact', 'start_date', 'end_date', 'notes',
    )


class JobsiteAddressEndpoint(ApiEndpoint):
    model = hr_models.JobsiteAddress
    filter_class = hr_filters.JobsiteAddressFilter
    serializer = vacancy_serializers.JobsiteAddressSerializer

    fieldsets = ('address', 'jobsite', 'regular_company', )

    list_editable = (
        {
            'label': _('Address'),
            'type': constants.FIELD_LINK,
            'field': '__str__',
            'endpoint': format_lazy(
                '{}{{id}}/',
                api_reverse_lazy('hr/jobsiteaddresses')
            ),
        }, 'jobsite.primary_contact', 'jobsite.start_date', 'jobsite.end_date', 'jobsite.notes',
    )


class FavouriteListEndpoint(ApiEndpoint):

    model = hr_models.FavouriteList
    serializer_fields = [
        '__all__',
        {
            'company': ['id', 'name', 'manager'],
        }
    ]
    fieldsets = ('candidate_contact', 'company_contact', 'company', 'jobsite', 'vacancy')
    list_display = (
        'company_contact', 'candidate_contact', {
            'field': 'company.manager',
            'label': _('Company Manager'),
        }, 'company', 'jobsite', 'vacancy',
    )
    list_editable = {
        'default': (
            'company_contact', {
                'field': 'company.manager',
                'label': _('Company Manager'),
            }, 'company', 'jobsite', 'vacancy',
        ),
        'vacancy': (
            'company_contact', 'candidate_contact', 'vacancy', {
                'label': _('Actions'),
                'delim': ' ',
                'fields': (constants.BUTTON_DELETE,)
            },
        )
    }
    list_filter = [
        'company_contact', 'candidate_contact', 'company', 'jobsite', 'vacancy'
    ]


class VacancyOfferEndpoint(ApiEndpoint):
    model = hr_models.VacancyOffer
    base_viewset = hr_viewsets.VacancyOfferViewset
    serializer = vacancy_serializers.VacancyOfferSerializer
    filter_class = hr_filters.VacancyOfferFilter

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
                'endpoint': format_lazy('{}{{id}}/accept', api_reverse_lazy('hr/vacancyoffers')),
                'text_color': '#5cb85c',
                'title': _('Accept'),
            }, {
                'type': constants.FIELD_BUTTON,
                'icon': 'fa-minus-circle',
                'field': 'has_cancel_action',
                'action': constants.DEFAULT_ACTION_POST,
                'endpoint': format_lazy('{}{{id}}/cancel', api_reverse_lazy('hr/vacancyoffers')),
                'text_color': '#f32700',
                'title': _('Cancel'),
            }, {
                'type': constants.FIELD_BUTTON,
                'icon': 'fa-commenting',
                'field': 'has_resend_action',
                'action': constants.DEFAULT_ACTION_POST,
                'endpoint': format_lazy('{}{{id}}/resend', api_reverse_lazy('hr/vacancyoffers')),
                'text_color': '#f0ad4e',
                'title': _('Resend VO'),
            }, constants.BUTTON_DELETE),
        }
    )
    ordering = ('-shift.date.shift_date', )
    list_filter = ['candidate_contact']


class CarrierListEndpoint(ApiEndpoint):
    model = hr_models.CarrierList

    list_display = ('candidate_contact', 'target_date', 'confirmed_available', 'vacancy_offer')
    list_editable = ('target_date', 'confirmed_available', 'vacancy_offer')


class BlackListEndpoint(ApiEndpoint):
    model = hr_models.BlackList

    list_display = ('company', 'candidate_contact', 'timesheet', 'jobsite')
    list_editable = ('company', 'timesheet', 'jobsite')


class CandidateEvaluationEndpoint(ApiEndpoint):
    model = hr_models.CandidateEvaluation

    list_display = ('candidate_contact', 'supervisor', 'evaluated_at')
    list_editable = (
        'supervisor', 'evaluated_at', 'level_of_communication', 'was_on_time', 'was_motivated', 'had_ppe_and_tickets',
        'met_expectations', 'representation', 'reference_timesheet'
    )
    fieldsets = (
        'candidate_contact', 'supervisor', {
            'field': 'evaluated_at',
            'read_only': False,
            'type': constants.FIELD_DATETIME,
        }, 'level_of_communication', 'was_on_time', 'was_motivated',
        'had_ppe_and_tickets', 'met_expectations', 'representation', 'reference_timesheet'
    )


class VacancyEndpoint(ApiEndpoint):
    model = hr_models.Vacancy
    base_viewset = hr_viewsets.VacancyViewset
    serializer = vacancy_serializers.VacancySerializer
    filter_class = hr_filters.VacancyFilter

    list_display = ('workers', 'work_start_date', {
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
            'text': _('Cancel Vacancy Dates'),
            'action': constants.DEFAULT_ACTION_EDIT,
            'hidden': 'no_vds',
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
        'label': _("Today's timesheets"),
        'name': 'timesheets',
        'fields': ({
            'field': 'todays_timesheets',
            'type': constants.FIELD_STATIC,
            'title': _('going to work/submitted timesheet/supervisor approved'),
        },)
    }, {
        'label': _("Activities"),
        'delim': '/',
        'title': _('actual / overdue / total'),
        'fields': ({
            'field': 'actual_activities',
            'type': constants.FIELD_LINK,
            'link': '/activity/activities/',
        }, {
            'field': 'overdue_activities',
            'type': constants.FIELD_LINK,
            'link': '/activity/activities/',
        }, {
            'field': 'total_activities',
            'type': constants.FIELD_LINK,
            'link': '/activity/activities/',
        },)
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
        'workers', 'jobsite__jobsite_addresses__address__city__search_names', 'publish_on', 'expires_on',
        'jobsite__jobsite_addresses__address__street_address', 'jobsite__master_company__name', 'position__name'
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
                    }, {
                        'label': _('Client representative'),
                        'field': 'customer_representative',
                        'type': constants.FIELD_RELATED,
                    }, {
                        'label': _('Provider company'),
                        'field': 'provider_company',
                        'type': constants.FIELD_RELATED,
                        'query': {
                            'type': 'master',
                        }
                    }, {
                        'label': _('Company representative'),
                        'field': 'provider_representative',
                        'type': constants.FIELD_RELATED,
                        'query': {
                            'company': '{provider_company.id}',
                        }
                    }, {
                        'label': _('Accepted at'),
                        'field': 'provider_signed_at',
                        'type': constants.FIELD_DATETIME,
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
                        }
                    }, {
                        'label': _('Position'),
                        'field': 'position',
                        'type': constants.FIELD_RELATED,
                        'query': {
                            'company': '{customer_company.id}',
                        }
                    }, {
                        'field': 'work_start_date',
                        'type': constants.FIELD_DATE,
                        'default': datetime.date.today(),
                    }, 'default_shift_starting_time',
                    {
                        'type': constants.FIELD_RELATED,
                        'label': _('Candidate rate default'),
                        'query': {
                            'skill': '{position.id}',
                        },
                        'field': 'hourly_rate_default',
                        'values': ['hourly_rate'],
                        'display': '${hourly_rate}/h',
                    }
                )
            }
        )
    }, {
        'type': constants.FIELD_LIST,
        'field': 'id_',
        'query': {
            'vacancy': '{id}',
        },
        'label': _('Vacancy Dates'),
        'add_label': _('Add'),
        'add_endpoint': api_reverse_lazy('hr/vacancydates'),
        'endpoint': api_reverse_lazy('hr/shifts'),
        'prefilled': {
            'vacancy': '{id}',
        },
        'add_metadata_query': {
            'fieldsets_type': 'vacancy',
        },
    }, {
        'type': constants.FIELD_LIST,
        'field': 'id_',
        'query': {
            'vacancy': '{id}',
        },
        'label': _('Vacancy Offers'),
        'add_label': _('Fill in'),
        'add_endpoint': format_lazy('{}{{id}}/fillin/', api_reverse_lazy('hr/vacancies')),
        'endpoint': api_reverse_lazy('hr/vacancyoffers'),
        'add_metadata_query': {
            'type': 'list',
        },
    }, {
        'type': constants.CONTAINER_ROW,
        'label': _('Vacancy state timeline'),
        'fields': (
            {
                'type': constants.FIELD_TIMELINE,
                'label': _('States Timeline'),
                'field': 'id',
                'endpoint': format_lazy('{}timeline/', api_reverse_lazy('core/workflownodes')),
                'query': {
                    'model': 'hr.vacancy',
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
            'editable_type': 'vacancy',
        },
        'label': _('Favourite List'),
        'add_label': _('Add'),
        'endpoint': api_reverse_lazy('hr/favouritelists'),
        'prefilled': {
            'company_contact': '{customer_representative.id}',
            'vacancy': '{id}',
        }
    })

    def get_list_filter(self):
        states_part = partial(
            core_models.WorkflowNode.get_model_all_states, hr_models.Vacancy
        )
        list_filter = [{
                'type': constants.FIELD_DATE,
                'label': _('Shift start date'),
                'field': 'vacancy_dates.shift_date',
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
    serializer = vacancy_serializers.ShiftSerializer
    filter_class = hr_filters.ShiftFilter

    list_displzy = ('workers', 'time')

    fieldsets = ('date', 'time', 'workers', 'hourly_rate')

    list_editable = {
        'default': (
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
            }, {
                'label': _('Actions'),
                'delim': ' ',
                'fields': (constants.BUTTON_DELETE,)
            },
        ),
        'vacancy_date': (
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
            }, {
                'label': _('Actions'),
                'delim': ' ',
                'fields': (constants.BUTTON_DELETE,)
            },
        )
    }

    ordering = ('-date.shift_date', '-time')

    search_fields = ('date__vacancy', )

    list_editable_buttons = []


class VacancyDateEndpoint(ApiEndpoint):
    model = hr_models.VacancyDate

    fieldsets = {
        'default': (
            'vacancy', 'shift_date', 'workers', 'hourly_rate',
            {
                'type': constants.FIELD_LIST,
                'field': 'id_',
                'query': {
                    'date': '{id}',
                },
                'metadata_query': {
                    'editable_type': 'vacancy_date',
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
        'vacancy': (
            {
                'type': constants.FIELD_RELATED,
                'field': 'vacancy',
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
                    'editable_type': 'vacancy_date',
                },
                'label': _('Shifts'),
                'add_label': _('Add'),
                'endpoint': api_reverse_lazy('hr/shifts'),
                'prefilled': {
                    'date': '{id}',
                },
                'delay': True,
                'default': {
                    'date': '{id}'
                },
                'unique': ('time', )
            },
        ),
    }


class CandidateJobOfferEndpoint(ApiEndpoint):
    model = hr_models.VacancyOffer
    serializer = vacancy_serializers.CandidateJobOfferSerializer
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
        'shift.date.vacancy.position',
        {
            'field': 'shift.date.vacancy.customer_company',
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
            'field': 'shift.date.vacancy.jobsite.primary_contact',
        }, {
            'label': _('Status'),
            'fields': (
                {
                    'type': constants.FIELD_BUTTON,
                    'icon': 'fa-check-circle',
                    'field': 'hide_buttons',
                    'action': constants.DEFAULT_ACTION_POST,
                    'endpoint': format_lazy('{}{{id}}/accept', api_reverse_lazy('hr/vacancyoffers')),
                    'color': 'success',
                    'text': _('Accept'),
                    'hidden': 'hide_buttons',
                }, {
                    'type': constants.FIELD_BUTTON,
                    'icon': 'fa-times-circle',
                    'field': 'hide_buttons',
                    'action': constants.DEFAULT_ACTION_POST,
                    'endpoint': format_lazy('{}{{id}}/cancel', api_reverse_lazy('hr/vacancyoffers')),
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
router.register(endpoint=JobsiteAddressEndpoint())
router.register(endpoint=VacancyEndpoint())
router.register(endpoint=VacancyDateEndpoint())
router.register(endpoint=ShiftEndpoint())
router.register(endpoint=TimeSheetEndpoint())
router.register(endpoint=ExtranetCandidateTimesheetEndpoint(), url='hr/timesheets-candidate')
router.register(hr_models.TimeSheetIssue)
router.register(endpoint=VacancyOfferEndpoint())
router.register(endpoint=CandidateEvaluationEndpoint())
router.register(endpoint=BlackListEndpoint())
router.register(endpoint=FavouriteListEndpoint())
router.register(endpoint=CarrierListEndpoint())
router.register(hr_models.Payslip)
router.register(hr_models.PayslipLine)
router.register(hr_models.PayslipRule)
router.register(endpoint=InvoiceEndpoint(), replace=True)
router.register(endpoint=CandidateJobOfferEndpoint(), url='hr/joboffers-candidate')
