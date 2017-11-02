import pytest
from datetime import date

from django.contrib.contenttypes.models import ContentType

from r3sourcer.apps.core.models import Company
from r3sourcer.apps.pricing.models import (
    Industry, IndustryPriceList, IndustryPriceListRate, PriceList,
    PriceListRate, RateCoefficientGroup, RateCoefficient,
    RateCoefficientModifier, DynamicCoefficientRule,
)
from r3sourcer.apps.skills.models import Skill


industry_fake = Industry(type='test')
skill_f = Skill(name='skill')
rate_coeff_fake = RateCoefficient(name='coefficient')


str_test_data = [
    (industry_fake, 'test'),
    (IndustryPriceList(industry=industry_fake, valid_from=date(2017, 1, 1)),
        'test: 01/01/2017'),
    (IndustryPriceList(industry=industry_fake, valid_from=date(2017, 1, 1),
                       valid_until=date(2017, 2, 1)),
        'test: 01/01/2017 - 01/02/2017'),
    (PriceList(company=Company(name='company'), valid_from=date(2017, 1, 1)),
        'company: 01/01/2017'),
    (PriceList(company=Company(name='company'), valid_from=date(2017, 1, 1),
               valid_until=date(2017, 2, 1)),
        'company: 01/01/2017 - 01/02/2017'),
    (IndustryPriceListRate(skill=skill_f, hourly_rate=1.23), 'skill: $1.23/h'),
    (PriceListRate(skill=skill_f, hourly_rate=1.23), 'skill: $1.23/h'),
    (RateCoefficientGroup(name='group'), 'group'),
    (rate_coeff_fake, 'coefficient'),
    (RateCoefficientModifier(rate_coefficient=rate_coeff_fake,
                             fixed_override=1.23), 'coefficient: $1.23/h'),
    (RateCoefficientModifier(rate_coefficient=rate_coeff_fake,
                             multiplier=1.23, fixed_addition=2.34),
        'coefficient: *1.23+2.34'),
]


@pytest.mark.django_db
class TestStr:

    @pytest.mark.parametrize(['obj', 'str_result'], str_test_data)
    def test_str(self, obj, str_result):
        assert str(obj) == str_result

    def test_dynamic_coeff_str(self):
        ct = ContentType.objects.get_by_natural_key(
            'pricing', 'industry'
        )
        obj = DynamicCoefficientRule(rate_coefficient=rate_coeff_fake,
                                     rule_type=ct)

        assert str(obj) == 'coefficient: Industry'


@pytest.mark.django_db
class TestDynamicCoefficientRule:

    def test_save(self, rate_coefficient, monday_rule):
        obj = DynamicCoefficientRule(
            rate_coefficient=rate_coefficient,
            rule=monday_rule,
        )

        obj.save()

        assert obj.priority == 10

    def test_save_priority(self, rate_coefficient, monday_rule):
        obj = DynamicCoefficientRule(
            priority=20,
            rate_coefficient=rate_coefficient,
            rule=monday_rule,
        )

        obj.save()

        assert obj.priority == 20

    def test_save_manual_priority(self, rate_coefficient, monday_rule):
        obj = DynamicCoefficientRule(
            priority=20,
            rate_coefficient=rate_coefficient,
            rule=monday_rule,
        )

        obj.save()

        obj.priority = 0
        obj.save()

        assert obj.priority == 0
