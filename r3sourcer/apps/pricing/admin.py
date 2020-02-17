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

    list_display = ('__str__', 'master_company', 'industry')

    def master_company(self, obj):
        extra_obj = models.DynamicCoefficientRule.objects.filter(rule_id=obj.id)
        list_of_obj = []
        for i in extra_obj:
            for item in i.rate_coefficient.rate_coefficient_rels.all():
                list_of_obj.append(item.company)

        return list_of_obj
    master_company.allow_tags = True
    master_company.short_description = 'Master company'

    def industry(self, obj):
        extra_obj = models.DynamicCoefficientRule.objects.filter(
            rule_id=obj.id)
        list_of_obj = []
        for i in extra_obj:
            list_of_obj.append(i.rate_coefficient.industry)
        return list_of_obj


class RateCoefficientAdmin(admin.ModelAdmin):
    list_display = ('name', 'industry', 'master_company', 'rules')

    def master_company(self, obj):
        return [i.company for i in obj.rate_coefficient_rels.all()]


    def rules(self, obj):
        return [str(i) for i in obj.rate_coefficient_rules.all()]

    master_company.allow_tags = True
    master_company.short_description = 'Master company'


admin.site.register(models.Industry)

admin.site.register(models.RateCoefficientGroup)
admin.site.register(models.RateCoefficient, RateCoefficientAdmin)
admin.site.register(models.PriceList)
admin.site.register(models.PriceListRate)
admin.site.register(models.PriceListRateCoefficient)
admin.site.register(models.RateCoefficientModifier)
admin.site.register(models.DynamicCoefficientRule)
admin.site.register(models.RateCoefficientRel)
admin.site.register(models.PriceListRateModifier)

admin.site.register(models.WeekdayWorkRule, RateCoefficientForRulesAdmin)
admin.site.register(models.OvertimeWorkRule, RateCoefficientForRulesAdmin)
admin.site.register(models.TimeOfDayWorkRule, RateCoefficientForRulesAdmin)
admin.site.register(models.AllowanceWorkRule, RateCoefficientForRulesAdmin)
