from django.contrib import admin

from . import models


class TimeSheetAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'regular_company')


class JobsiteAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'industry')
    search_fields = ('short_name',)


admin.site.register(models.Jobsite, JobsiteAdmin)
admin.site.register(models.JobsiteUnavailability)
admin.site.register(models.Job)
admin.site.register(models.ShiftDate)
admin.site.register(models.Shift)
admin.site.register(models.TimeSheet, TimeSheetAdmin)
admin.site.register(models.TimeSheetIssue)
admin.site.register(models.JobOffer)
admin.site.register(models.CandidateEvaluation)
admin.site.register(models.CandidateScore)
admin.site.register(models.BlackList)
admin.site.register(models.FavouriteList)
admin.site.register(models.CarrierList)
admin.site.register(models.Payslip)
admin.site.register(models.PayslipLine)
admin.site.register(models.PayslipRule)
