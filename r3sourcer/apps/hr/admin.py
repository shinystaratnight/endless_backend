from django.contrib import admin
from django.db.models import Q
from . import models


class TimeSheetRateInline(admin.TabularInline):
    model = models.TimeSheetRate
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "worktype" and request._obj_:
            kwargs["queryset"] = models.WorkType.objects.filter(Q(skill_name=request._obj_.job_offer.shift.date.job.position.name) | \
                                                                Q(skill=request._obj_.job_offer.shift.date.job.position))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ClientTimeSheetFilesInline(admin.TabularInline):
    model = models.ClientTimeSheetFiles
    extra = 0


class CandidateTimeSheetFilesInline(admin.TabularInline):
    model = models.CandidateTimeSheetFiles
    extra = 0


class TimeSheetAdmin(admin.ModelAdmin):
    list_display = ('created_at', '__str__', 'regular_company', 'shift_started_at')
    ordering = ['-shift_started_at']
    inlines = [TimeSheetRateInline, ClientTimeSheetFilesInline, CandidateTimeSheetFilesInline]

    def get_form(self, request, obj=None, **kwargs):
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)


class JobRateInline(admin.TabularInline):
    model = models.JobRate
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "worktype" and request._obj_:
            kwargs["queryset"] = models.WorkType.objects.filter(Q(skill_name=request._obj_.position.name) | \
                                                                Q(skill=request._obj_.position))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class JobAdmin(admin.ModelAdmin):
    list_display = ('jobsite', 'position')
    search_fields = ('jobsite', 'position')
    inlines = [JobRateInline]


    def get_form(self, request, obj=None, **kwargs):
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)


class JobsiteAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'industry')
    search_fields = ('short_name',)


class JobOfferAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'candidate_contact', 'status')
    search_fields = ('short_name',)
    ordering = ['-created_at']


admin.site.register(models.Jobsite, JobsiteAdmin)
admin.site.register(models.JobsiteUnavailability)
admin.site.register(models.Job, JobAdmin)
admin.site.register(models.JobTag)
admin.site.register(models.ShiftDate)
admin.site.register(models.Shift)
admin.site.register(models.TimeSheet, TimeSheetAdmin)
admin.site.register(models.TimeSheetIssue)
admin.site.register(models.JobOffer, JobOfferAdmin)
admin.site.register(models.CandidateEvaluation)
admin.site.register(models.CandidateScore)
admin.site.register(models.BlackList)
admin.site.register(models.FavouriteList)
admin.site.register(models.CarrierList)
admin.site.register(models.Payslip)
admin.site.register(models.PayslipLine)
admin.site.register(models.PayslipRule)
