from datetime import timedelta
from itertools import chain

from .models import (
    RateCoefficient, PriceList, RateCoefficientModifier, IndustryPriceList,
    PriceListRateCoefficient, IndustryRateCoefficient,
)
from .exceptions import RateNotApplicable


class CoefficientService:

    def get_industry_rate_coefficient(self, industry, modifier_type,
                                      start_datetime, skill=None):
        industry_price_lists = IndustryPriceList.objects.filter(
            industry=industry
        )
        if skill:
            industry_price_lists = industry_price_lists.filter(
                industry_price_list_rates__skill=skill
            )
        industry_rate_coeff_ids = IndustryRateCoefficient.objects.filter(
            industry_price_list__in=industry_price_lists
        ).values_list('rate_coefficient', flat=True).distinct()

        return RateCoefficient.objects.filter(
            id__in=industry_rate_coeff_ids,
            rate_coefficient_modifiers__type=modifier_type,
            active=True
        ).order_by('-priority')

    def process_rate_coefficients(self, rate_coefficients, start_datetime,
                                  worked_hours, break_started=None,
                                  break_ended=None):
        res = []
        for rate_coefficient in rate_coefficients:
            rules = rate_coefficient.rate_coefficient_rules.order_by(
                '-priority'
            )

            try:
                used_hours = worked_hours
                is_allowance = False
                for rule in rules:
                    hours = rule.rule.calc_hours(
                        start_datetime, worked_hours, break_started,
                        break_ended
                    )
                    if hours == timedelta(hours=-1):
                        is_allowance = True
                        hours = timedelta(hours=1)

                    used_hours = min(hours, used_hours)

                    if used_hours.total_seconds() <= 0:
                        break

                if used_hours.total_seconds() > 0 or is_allowance:
                    res.append({
                        'coefficient': rate_coefficient,
                        'hours': used_hours
                    })

                    if not is_allowance:
                        worked_hours -= used_hours
            except RateNotApplicable:
                pass

        if worked_hours.total_seconds() > 0:
            res.append({
                'coefficient': 'base',
                'hours': worked_hours
            })

        return res

    def calc(self, industry, modifier_type, start_datetime, worked_hours,
             break_started=None, break_ended=None):
        rate_coefficients = self.get_industry_rate_coefficient(
            industry, modifier_type, start_datetime
        )

        return self.process_rate_coefficients(
            rate_coefficients, start_datetime, worked_hours,
            break_started, break_ended
        )


class PriceListCoefficientService(CoefficientService):

    def get_rate_coefficients_for_company(self, company, industry, skill,
                                          start_datetime):
        price_lists = PriceList.objects.filter(
            company=company,
            price_list_rates__skill=skill,
        )
        rate_coeff_ids = PriceListRateCoefficient.objects.filter(
            price_list__in=price_lists
        ).values_list('rate_coefficient', flat=True).distinct()

        company_type = RateCoefficientModifier.TYPE_CHOICES.company
        rate_coefficients = RateCoefficient.objects.filter(
            id__in=rate_coeff_ids,
            rate_coefficient_modifiers__type=company_type,
            active=True,
        ).order_by('-priority')

        industry_rate_coeff = self.get_industry_rate_coefficient(
            industry, company_type, start_datetime, skill=skill
        ).exclude(name__in=rate_coefficients.values_list('name', flat=True))

        return chain(rate_coefficients, industry_rate_coeff)

    def calc_company(self, company, industry, skill, modifier_type,
                     start_datetime, worked_hours, break_started=None,
                     break_ended=None):
        rate_coefficients = self.get_rate_coefficients_for_company(
            company, industry, skill, modifier_type
        )

        return self.process_rate_coefficients(
            rate_coefficients, start_datetime, worked_hours,
            break_started, break_ended
        )