from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline

from . import models


class RulesInline(GenericTabularInline):
    ct_field = "rule_type"
    ct_fk_field = "rule_id"
    extra = 0
    model = models.DynamicCoefficientRule


class RateCoefficientForRulesAdmin(admin.ModelAdmin):
    inlines = [RulesInline]


class RateCoefficientAdmin(admin.ModelAdmin):
    list_display = ('name', 'industry')


admin.site.register(models.Industry)

admin.site.register(models.RateCoefficientGroup)
admin.site.register(models.RateCoefficient, RateCoefficientAdmin)
admin.site.register(models.PriceList)
admin.site.register(models.PriceListRate)
admin.site.register(models.PriceListRateCoefficient)
admin.site.register(models.RateCoefficientModifier)
admin.site.register(models.DynamicCoefficientRule)

admin.site.register(models.WeekdayWorkRule, RateCoefficientForRulesAdmin)
admin.site.register(models.OvertimeWorkRule, RateCoefficientForRulesAdmin)
admin.site.register(models.TimeOfDayWorkRule, RateCoefficientForRulesAdmin)
admin.site.register(models.AllowanceWorkRule, RateCoefficientForRulesAdmin)
