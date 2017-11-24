from django.utils.translation import ugettext_lazy as _
from drf_auto_endpoint.router import router

from r3sourcer.apps.core.api.endpoints import ApiEndpoint
from r3sourcer.apps.core_adapter import constants

from r3sourcer.apps.hr import models as hr_models
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

    serializer_fields = [
        '__all__',
        {
            'shift': ['id', 'time', {
                'date': ['shift_date'],
            }],
        }
    ]

    list_display = ('shift.date.shift_date', 'status')
    list_editable = ({
        'label': _('Shift date and time'),
        'fields': ('shift.date.shift_date', 'shift.time')
    }, 'status')
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


router.register(hr_models.Jobsite)
router.register(hr_models.JobsiteUnavailability)
router.register(hr_models.JobsiteAddress)
router.register(hr_models.Vacancy)
router.register(hr_models.VacancyDate)
router.register(hr_models.Shift)
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
