from django.contrib import admin

from . import models


class SkillNameLanguageInline(admin.TabularInline):
    model = models.SkillNameLanguage
    extra = 0

class WorkTypeInline(admin.TabularInline):
    model = models.WorkType
    extra = 0

class SkillNameAdmin(admin.ModelAdmin):
    list_display = ('name', 'industry', )
    inlines = [SkillNameLanguageInline, WorkTypeInline]


class WorkTypeLanguageInline(admin.TabularInline):
    model = models.WorkTypeLanguage
    extra = 0


class WorkTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'skill_name', )
    inlines = [WorkTypeLanguageInline]


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
admin.site.register(models.WorkType, WorkTypeAdmin)
