from django.utils.translation import ugettext_lazy as _
from drf_auto_endpoint.router import router

from r3sourcer.apps.core.api.endpoints import ApiEndpoint

from .. import models
from .payment import InvoiceEndpoint
from .timesheet_endpoint import TimeSheetEndpoint


class FavouriteListEndpoint(ApiEndpoint):

    model = models.FavouriteList
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


router.register(models.Jobsite)
router.register(models.JobsiteUnavailability)
router.register(models.JobsiteAddress)
router.register(models.Vacancy)
router.register(models.VacancyDate)
router.register(models.Shift)
router.register(endpoint=TimeSheetEndpoint())
router.register(models.TimeSheetIssue)
router.register(models.VacancyOffer)
router.register(models.CandidateEvaluation)
router.register(models.BlackList)
router.register(endpoint=FavouriteListEndpoint())
router.register(models.CarrierList)
router.register(models.Payslip)
router.register(models.PayslipLine)
router.register(models.PayslipRule)
router.register(endpoint=InvoiceEndpoint(), replace=True)
