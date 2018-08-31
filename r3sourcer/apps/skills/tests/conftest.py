import pytest

from r3sourcer.apps.core.models import Company
from r3sourcer.apps.pricing.models import PriceList, Industry
from r3sourcer.apps.skills.models import Skill, SkillName


@pytest.fixture
def industry(db):
    return Industry.objects.create(type='test')


@pytest.fixture
def company(db):
    return Company.objects.create(
        name='Company',
        business_id='111',
        registered_for_gst=True,
        type=Company.COMPANY_TYPES.master,
    )


@pytest.fixture
def skill_name(db, industry):
    return SkillName.objects.create(name="Driver", industry=industry)


@pytest.fixture
def skill(db, skill_name, company):
    return Skill.objects.create(
        name=skill_name,
        carrier_list_reserve=2,
        short_name="Drv",
        active=False,
        company=company
    )


@pytest.fixture
def price_list(db, company):
    return PriceList.objects.create(
        company=company,
    )
