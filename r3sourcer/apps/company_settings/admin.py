from django.contrib import admin

from . import models


class MYOBSettingsAdmin(admin.ModelAdmin):
    list_display = ('company' ,)
    search_fields = ('company__name',)


admin.site.register(models.MYOBSettings, MYOBSettingsAdmin)
admin.site.register(models.CompanySettings )
admin.site.register(models.MYOBAccount )

