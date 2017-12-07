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
from r3sourcer.apps.hr.endpoints.timesheet_endpoint import TimeSheetEndpoint


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
    list_editable = (
        'company_contact', {
            'field': 'company.manager',
            'label': _('Company Manager'),
        }, 'company', 'jobsite', 'vacancy',
    )
    list_filter = [
        'company_contact', 'candidate_contact', 'company', 'jobsite', 'vacancy'
    ]


class VacancyOfferEndpoint(ApiEndpoint):
    model = hr_models.VacancyOffer
    base_viewset = hr_viewsets.VacancyOfferViewset
    serializer = vacancy_serializers.VacancyOfferSerializer

    list_display = ('shift.date.shift_date', 'status')
    list_editable = (
        'candidate_contact', 'shift.date.shift_date', 'shift.time', 'status',
        {
            'label': _('Client/Candidate Rate'),
            'delim': ' / ',
            'fields': ({
                'field': 'client_rate',
                'type': constants.FIELD_STATIC,
            }, {
                'field': 'candidate_rate',
                'type': constants.FIELD_STATIC,
            })
        }, {
            'type': constants.FIELD_LINK,
            'label': _('Timesheets'),
            'field': 'timesheets',
            'text': _('Link to TimeSheet'),
            'link': format_lazy('{}{{field}}', api_reverse_lazy('hr/timesheets'))
        }, {
            'type': constants.FIELD_BUTTON,
            'icon': 'fa-times-circle',
            'field': 'id',
            'action': 'deleteOffer',
            'text_color': '#f32700',
            'label': _('Actions'),
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
            'action': 'cancelVDs',
            'hidden': 'no_vds',
            'field': 'id',
        }, {
            'type': constants.FIELD_BUTTON,
            'icon': 'fa-sign-in',
            'text': _('Fill-in'),
            'action': 'fillinVacancy',
            'hidden': 'can_fillin',
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
        'label': '{__str__}',
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
                    }, {
                        'label': _('Company representative'),
                        'field': 'provider_representative',
                        'type': constants.FIELD_RELATED,
                    }, {
                        'label': _('Accepted at'),
                        'field': 'provider_signed_at',
                        'type': constants.FIELD_DATETIME,
                    }
                )
            }, {
                'type': constants.CONTAINER_COLUMN,
                'fields': (
                    'jobsite', 'position', 'work_start_date', 'default_shift_starting_time', 'hourly_rate_default'
                )
            }
        )
    }, {
        'type': constants.FIELD_LIST,
        'field': 'id_',
        'query': {
            'date.vacancy': '{id}',
        },
        'label': _('Vacancy Dates'),
        'add_label': _('Add date'),
        'add_endpoint': api_reverse_lazy('hr/vacancydates'),
        'endpoint': api_reverse_lazy('hr/shifts'),
        'prefilled': {
            'date.vacancy': '{id}',
        }
    }, {
        'type': constants.FIELD_LIST,
        'field': 'id_',
        'query': {
            'shift.date.vacancy': '{id}',
        },
        'label': _('Vacancy Offers'),
        'add_label': _('Fill in'),
        'add_endpoint': api_reverse_lazy('hr/vacancyoffers'),
        'endpoint': api_reverse_lazy('hr/vacancyoffers'),
    })

    def get_list_filter(self):
        states_part = partial(
            core_models.WorkflowNode.get_model_all_states, hr_models.Vacancy
        )
        list_filter = [{
                'type': constants.FIELD_DATE,
                'label': _('Shift start date'),
                'field': 'vacancy_dates.shift_date',
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

    list_displzy = ('workers', 'time')

    fieldsets = ('date', 'time', 'workers', 'hourly_rate')

    list_editable = (
        {
            'type': constants.FIELD_DATE,
            'label': _('Date'),
            'name': 'date.shift_date',
            'field': 'date.shift_date',
        }, 'workers', 'hourly_rate', {
            'type': constants.FIELD_TEXT,
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
            'type': constants.FIELD_BUTTON,
            'icon': 'fa-times-circle',
            'field': 'id',
            'action': 'deleteShift',
            'color': '#f32700',
            'label': _('Actions'),
        }
    )
    ordering = ('-date.shift_date', '-time')

    search_fields = ('date__vacancy', )


class VacancyDateEndpoint(ApiEndpoint):
    model = hr_models.VacancyDate

    fieldsets = ('vacancy', 'shift_date', 'workers', 'hourly_rate')


router.register(hr_models.Jobsite, search_fields=(
    'jobsite_addresses__address__city__search_names', 'jobsite_addresses__address__street_address',
    'master_company__name'
))
router.register(hr_models.JobsiteUnavailability)
router.register(hr_models.JobsiteAddress)
router.register(endpoint=VacancyEndpoint())
router.register(endpoint=VacancyDateEndpoint())
router.register(endpoint=ShiftEndpoint())
router.register(endpoint=TimeSheetEndpoint())
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
