from django.contrib import admin

from . import models


class SkillNameAdmin(admin.ModelAdmin):
    list_display = ('name', 'industry', )


class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'industry', )

    def industry(self, obj):
        return obj.name.industry


admin.site.register(models.EmploymentClassification)
admin.site.register(models.Skill, SkillAdmin)
admin.site.register(models.SkillName, SkillNameAdmin)
admin.site.register(models.SkillBaseRate)
admin.site.register(models.SkillTag)
