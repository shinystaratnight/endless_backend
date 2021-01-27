from django.contrib import admin
import nested_admin

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


class SkillAdmin(admin.ModelAdmin):
    inlines = [SkillRateRangeInline]
    list_display = ('name', 'company', 'industry', )

    def industry(self, obj):
        return obj.name.industry


admin.site.register(models.EmploymentClassification)
admin.site.register(models.Skill, SkillAdmin)
admin.site.register(models.SkillName, SkillNameAdmin)
admin.site.register(models.SkillBaseRate)
admin.site.register(models.SkillTag)
