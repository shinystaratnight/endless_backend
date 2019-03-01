from django.contrib import admin

from . import models


class SMSBalanceAdmin(admin.ModelAdmin):
    list_display = ('company', 'balance',)
    search_fields = ('company__name',)


class TSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'status')
    list_filter = ('company',)
    readonly_fields = ('last_time_billed', 'sms_balance', 'current_period_start',
                       'current_period_end', 'worker_count', 'price', 'subscription_type',
                       'created')


class SubscriptionTypeAdmin(admin.ModelAdmin):

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.type == models.SubscriptionType.SUBSCRIPTION_TYPES.annual:
            return self.readonly_fields + ('start_range_price_monthly',)
        else:
            return self.readonly_fields + ('start_range_price_annual',)


class PaymentAdmin(admin.ModelAdmin):
    list_display = ('company', 'type', 'created')
    search_fields = ('company__name',)


admin.site.register(models.SMSBalance, SMSBalanceAdmin)
admin.site.register(models.Subscription, TSubscriptionAdmin)
admin.site.register(models.SubscriptionType, SubscriptionTypeAdmin)
admin.site.register(models.Payment, PaymentAdmin)
