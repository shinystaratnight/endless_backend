import pytest

from r3sourcer.apps.skills.models import (
    EmploymentClassification, Skill, SkillBaseRate
)


str_test_data = [
    (EmploymentClassification(name='test'), 'test'),
    (Skill(name='test'), 'test'),
    (SkillBaseRate(skill=Skill(name='t'), hourly_rate=1.23), 't $1.23/h'),
]


class TestStr:

    @pytest.mark.parametrize(['obj', 'str_result'], str_test_data)
    def test_str(self, obj, str_result):
        assert str(obj) == str_result
