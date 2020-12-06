from django.contrib import admin

from . import models


class CandidateContactAdmin(admin.ModelAdmin):
    search_fields = ('contact__first_name', 'contact__last_name', 'profile_price')


class CandidateRelAdmin(admin.ModelAdmin):
    search_fields = ('master_company__name', 'candidate_contact__contact__first_name',
                     'candidate_contact__contact__last_name')


class SkillRelAdmin(admin.ModelAdmin):
    list_display = ('candidate_contact', 'skill')
    search_fields = ('candidate_contact__contact__first_name', 'candidate_contact__contact__last_name')


class CountryVisaTypeRelationAdmin(admin.ModelAdmin):
    ordering = ('name',)


admin.site.register(models.VisaType)
admin.site.register(models.CountryVisaTypeRelation)
admin.site.register(models.SuperannuationFund)
admin.site.register(models.CandidateContact, CandidateContactAdmin)
admin.site.register(models.TagRel)
admin.site.register(models.SkillRel, SkillRelAdmin)
admin.site.register(models.InterviewSchedule)
admin.site.register(models.CandidateRel, CandidateRelAdmin)
admin.site.register(models.Subcontractor)
admin.site.register(models.SubcontractorCandidateRelation)
