from django.contrib import admin

from . import models

admin.site.register(models.AcceptanceTest)
admin.site.register(models.AcceptanceTestAnswer)
admin.site.register(models.AcceptanceTestQuestion)
admin.site.register(models.AcceptanceTestSkill)
