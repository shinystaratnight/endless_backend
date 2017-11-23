from django.utils.translation import ugettext_lazy as _
from drf_auto_endpoint.router import router

from r3sourcer.apps.core.api.endpoints import ApiEndpoint

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

    list_display = (
        'company_contact', 'candidate_contact', {
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
            'shift': ['id', {
                'date': ['shift_date'],
            }],
        }
    ]

    list_display = (
        'shift.date.shift_date',
    )

    fieldsets = ('shift.date.shift_date', )
    ordering = ('-shift.date.shift_date', )


class CarrierListEndpoint(ApiEndpoint):
    model = hr_models.CarrierList

    list_display = ('candidate_contact', 'target_date', 'confirmed_available')


class BlackListEndpoint(ApiEndpoint):
    model = hr_models.BlackList

    list_display = ('company', 'candidate_contact', 'timesheet', 'jobsite')


class CandidateEvaluationEndpoint(ApiEndpoint):
    model = hr_models.CandidateEvaluation

    list_display = ('candidate_contact', 'supervisor', 'evaluated_at')


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
