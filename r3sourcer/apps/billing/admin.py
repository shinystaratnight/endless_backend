from django.contrib import admin

from . import models


class SMSBalanceAdmin(admin.ModelAdmin):
    list_display = ('company', 'balance',)
    search_fields = ('company__name',)


class TSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'status')
    list_filter = ('company',)
    readonly_fields = ('company', 'last_time_billed', 'sms_balance', 'current_period_start',
                       'current_period_end', 'worker_count', 'price', 'subscription_type',
                       'created')


admin.site.register(models.SMSBalance, SMSBalanceAdmin)
admin.site.register(models.Subscription, TSubscriptionAdmin)
admin.site.register(models.SubscriptionType)
admin.site.register(models.Payment)
