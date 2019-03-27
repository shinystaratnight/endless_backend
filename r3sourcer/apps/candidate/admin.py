from django.contrib import admin

from . import models


class CandidateContactAdmin(admin.ModelAdmin):
    search_fields = ('contact__first_name', 'contact__last_name')


admin.site.register(models.VisaType)
admin.site.register(models.SuperannuationFund)
admin.site.register(models.CandidateContact, CandidateContactAdmin)
admin.site.register(models.TagRel)
admin.site.register(models.SkillRel)
admin.site.register(models.InterviewSchedule)
admin.site.register(models.CandidateRel)
admin.site.register(models.Subcontractor)
admin.site.register(models.SubcontractorCandidateRelation)
