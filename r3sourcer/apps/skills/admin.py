from django.contrib import admin

from . import models


class SkillNameAdmin(admin.ModelAdmin):
    list_display = ('name', 'industry', )


admin.site.register(models.EmploymentClassification)
admin.site.register(models.Skill)
admin.site.register(models.SkillName, SkillNameAdmin)
admin.site.register(models.SkillBaseRate)
admin.site.register(models.SkillTag)
