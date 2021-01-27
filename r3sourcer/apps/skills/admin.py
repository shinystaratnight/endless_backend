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
    extra = 0
    inlines = [WorkTypeLanguageInline]


class SkillNameAdmin(nested_admin.NestedModelAdmin):
    list_display = ('name', 'industry', )
    inlines = [SkillNameLanguageInline, WorkTypeInline]


class SkillRateRangeInline(admin.TabularInline):
    model = models.SkillRateRange
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "worktype":
            kwargs["queryset"] = models.WorkType.objects.filter(skill_name=request._obj_.name)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'industry', )
    search_fields = ['name', 'company']
    list_filter = (('company', ObjectRelatedDropdownFilter),)
    inlines = [SkillRateRangeInline]

    def industry(self, obj):
        return obj.name.industry

    def get_form(self, request, obj=None, **kwargs):
        # just save obj reference for future processing in Inline
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)


admin.site.register(models.EmploymentClassification)
admin.site.register(models.Skill, SkillAdmin)
admin.site.register(models.SkillName, SkillNameAdmin)
# admin.site.register(models.SkillBaseRate)
admin.site.register(models.SkillTag)
