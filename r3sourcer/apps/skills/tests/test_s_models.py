import pytest

from r3sourcer.apps.skills.models import EmploymentClassification, Skill, SkillBaseRate
from r3sourcer.apps.pricing.models import PriceListRate


str_test_data = [
    (EmploymentClassification(name='test'), 'test'),
    (Skill(name='test'), 'test'),
    (SkillBaseRate(skill=Skill(name='t'), hourly_rate=1.23), 't $1.23/h'),
]


class TestStr:
    @pytest.mark.parametrize(['obj', 'str_result'], str_test_data)
    def test_str(self, obj, str_result):
        assert str(obj) == str_result


class TestSkillBaseRate:
    def test_validation(self, skill):
        SkillBaseRate.objects.create(skill=skill, hourly_rate=1, default_rate=True)

        with pytest.raises(Exception) as excinfo:
            SkillBaseRate.objects.create(skill=skill, hourly_rate=2, default_rate=True)

        assert excinfo.value.messages[0] == 'Only one rate for the skill can be set to "True"'

    @pytest.mark.django_db
    def test_default_rate(self):
        skill = Skill.objects.create(name="Driver", carrier_list_reserve=2, short_name="Drv", active=False)
        base_rate = SkillBaseRate.objects.create(skill=skill, hourly_rate=20, default_rate=False)
        base_rate2 = SkillBaseRate.objects.create(skill=skill, hourly_rate=30, default_rate=False)

        assert base_rate.default_rate
        assert not base_rate2.default_rate


class TestSkill:
    def test_validation_success(self, price_list):
        skill = Skill.objects.create(name="Driver", carrier_list_reserve=2, short_name="Drv", active=False)
        SkillBaseRate.objects.create(skill=skill, hourly_rate=20, default_rate=True)
        PriceListRate.objects.create(skill=skill, price_list=price_list, default_rate=True)
        skill.active = True
        skill.save()

        assert skill.active

    def test_validation_fail(self, skill):
        SkillBaseRate.objects.create(skill=skill, hourly_rate=20, default_rate=True)
        skill.active = True

        with pytest.raises(Exception) as excinfo:
            skill.save()

        assert excinfo.value.messages[0] == 'Skill cant be active it doesnt have default price list rate and defalut base rate.'
