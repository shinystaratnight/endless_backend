from django.contrib import admin

from r3sourcer.apps.skills.models import Skill
from . import models


class SkillRelInline(admin.TabularInline):
    model = models.SkillRel
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "skill" and request._obj_:
            kwargs["queryset"] = Skill.objects.filter(company=request._obj_.get_closest_company())
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class FormalityInline(admin.TabularInline):
    model = models.Formality
    extra = 0


class TagRelInline(admin.TabularInline):
    model = models.TagRel
    extra = 0


class CandidateContactAdmin(admin.ModelAdmin):
    list_display = ('contact', 'recruitment_agent', 'is_active')
    search_fields = ('contact__first_name', 'contact__last_name', 'profile_price')
    inlines = [SkillRelInline, FormalityInline, TagRelInline]

    def is_active(self, obj):
        return obj.contact.user.is_active

    def get_form(self, request, obj=None, **kwargs):
        # just save obj reference for future processing in Inline
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)


class CandidateRelAdmin(admin.ModelAdmin):
    search_fields = ('master_company__name', 'candidate_contact__contact__first_name',
                     'candidate_contact__contact__last_name')


class CountryVisaTypeRelationAdmin(admin.ModelAdmin):
    ordering = ('name',)


admin.site.register(models.VisaType)
admin.site.register(models.CountryVisaTypeRelation)
admin.site.register(models.SuperannuationFund)
admin.site.register(models.CandidateContact, CandidateContactAdmin)
admin.site.register(models.TagRel)
admin.site.register(models.InterviewSchedule)
admin.site.register(models.CandidateRel, CandidateRelAdmin)
admin.site.register(models.Subcontractor)
admin.site.register(models.SubcontractorCandidateRelation)
