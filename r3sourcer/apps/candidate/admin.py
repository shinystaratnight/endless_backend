from django.contrib import admin

from . import models

admin.site.register(models.VisaType)
admin.site.register(models.SuperannuationFund)
admin.site.register(models.CandidateContact)
admin.site.register(models.TagRel)
admin.site.register(models.SkillRel)
admin.site.register(models.SkillRateRel)
admin.site.register(models.InterviewSchedule)
admin.site.register(models.CandidateRel)
