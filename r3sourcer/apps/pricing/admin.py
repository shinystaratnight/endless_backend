from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline

from . import models


class RulesInline(GenericTabularInline):
    ct_field = "rule_type"
    ct_fk_field = "rule_id"
    extra = 0
    model = models.DynamicCoefficientRule


class RateCoefficientAdmin(admin.ModelAdmin):
    inlines = [RulesInline]


admin.site.register(models.Industry)

admin.site.register(models.RateCoefficientGroup)
admin.site.register(models.RateCoefficient)
admin.site.register(models.PriceList)
admin.site.register(models.PriceListRate)
admin.site.register(models.PriceListRateCoefficient)
admin.site.register(models.RateCoefficientModifier)
admin.site.register(models.DynamicCoefficientRule)

admin.site.register(models.WeekdayWorkRule, RateCoefficientAdmin)
admin.site.register(models.OvertimeWorkRule, RateCoefficientAdmin)
admin.site.register(models.TimeOfDayWorkRule, RateCoefficientAdmin)
admin.site.register(models.AllowanceWorkRule, RateCoefficientAdmin)
