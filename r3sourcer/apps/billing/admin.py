from django.contrib import admin

from . import models


class SMSBalanceAdmin(admin.ModelAdmin):

    list_display = ('company', 'balance', )
    search_fields = ('company__name', )


admin.site.register(models.SMSBalance, SMSBalanceAdmin)
