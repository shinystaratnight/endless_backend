from django import forms
from django.db.models import Q
from django.contrib import admin
import nested_admin

from r3sourcer.apps.core_utils.filters import ObjectRelatedDropdownFilter
from . import models


class SkillNameLanguageInline(nested_admin.NestedTabularInline):
    model = models.SkillNameLanguage
    extra = 0


class WorkTypeLanguageInline(nested_admin.NestedTabularInline):
    model = models.WorkTypeLanguage
    extra = 0


class WorkTypeInline(nested_admin.NestedTabularInline):
    model = models.WorkType
    exclude = ['skill']
    extra = 0
    inlines = [WorkTypeLanguageInline]


class SkillNameAdmin(nested_admin.NestedModelAdmin):
    list_display = ('name', 'industry', )
    inlines = [SkillNameLanguageInline, WorkTypeInline]


class SkillRateRangeInline(nested_admin.NestedTabularInline):
    model = models.SkillRateRange
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "worktype" and request._obj_:
            kwargs["queryset"] = models.WorkType.objects.filter(Q(skill_name=request._obj_.name) | \
                                                                Q(skill=request._obj_))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class WorkTypeSkillInline(nested_admin.NestedTabularInline):
    model = models.WorkType
    exclude = ['skill_name']
    extra = 0
    inlines = [WorkTypeLanguageInline]

class SkillAdmin(nested_admin.NestedModelAdmin):
    list_display = ('name', 'company', 'industry', )
    search_fields = ['name__name', 'company__name']
    list_filter = (('company', ObjectRelatedDropdownFilter),)
    inlines = [WorkTypeSkillInline, SkillRateRangeInline]

    def industry(self, obj):
        return obj.name.industry

    def get_form(self, request, obj=None, **kwargs):
        # just save obj reference for future processing in Inline
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)


admin.site.register(models.EmploymentClassification)
admin.site.register(models.Skill, SkillAdmin)
admin.site.register(models.SkillName, SkillNameAdmin)
admin.site.register(models.WorkType)
admin.site.register(models.SkillTag)
