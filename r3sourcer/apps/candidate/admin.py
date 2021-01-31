from django.contrib import admin

from . import models


class FormalityInline(admin.TabularInline):
    model = models.Formality
    extra = 0


class CandidateContactAdmin(admin.ModelAdmin):
    search_fields = ('contact__first_name', 'contact__last_name', 'profile_price')
    inlines = [FormalityInline]


class CandidateRelAdmin(admin.ModelAdmin):
    search_fields = ('master_company__name', 'candidate_contact__contact__first_name',
                     'candidate_contact__contact__last_name')


class SkillRateInline(admin.TabularInline):
    model = models.SkillRate
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "worktype":
            kwargs["queryset"] = models.WorkType.objects.filter(skill_name=request._obj_.skill.name)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class SkillRelAdmin(admin.ModelAdmin):
    list_display = ('candidate_contact', 'skill')
    search_fields = ('candidate_contact__contact__first_name', 'candidate_contact__contact__last_name')
    inlines = [SkillRateInline]

    def get_form(self, request, obj=None, **kwargs):
        # just save obj reference for future processing in Inline
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)


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
