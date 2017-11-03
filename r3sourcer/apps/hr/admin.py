from django.contrib import admin

from . import models

admin.site.register(models.Jobsite)
admin.site.register(models.JobsiteUnavailability)
admin.site.register(models.JobsiteAddress)
admin.site.register(models.Vacancy)
admin.site.register(models.VacancyDate)
admin.site.register(models.Shift)
admin.site.register(models.TimeSheet)
admin.site.register(models.TimeSheetIssue)
admin.site.register(models.VacancyOffer)
admin.site.register(models.CandidateEvaluation)
admin.site.register(models.BlackList)
admin.site.register(models.FavouriteList)
admin.site.register(models.CarrierList)
admin.site.register(models.Payslip)
admin.site.register(models.PayslipLine)
admin.site.register(models.PayslipRule)
