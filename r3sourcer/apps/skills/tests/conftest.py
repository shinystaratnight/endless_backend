import pytest

from r3sourcer.apps.core.models import Company
from r3sourcer.apps.pricing.models import PriceList, Industry, IndustryPriceList
from r3sourcer.apps.skills.models import Skill


@pytest.fixture
def industry(db):
    return Industry.objects.create(type='test')


@pytest.fixture
def industry_price_list(db, industry):
    return IndustryPriceList.objects.create(
        industry=industry,
    )


@pytest.fixture
def company(db):
    return Company.objects.create(
        name='Company',
        business_id='111',
        registered_for_gst=True,
        type=Company.COMPANY_TYPES.master,
    )


@pytest.fixture
def skill(db):
    return Skill.objects.create(
        name="Driver",
        carrier_list_reserve=2,
        short_name="Drv",
        active=False
    )


@pytest.fixture
def price_list(db, company, industry_price_list):
    return PriceList.objects.create(
        company=company,
        industry_price_list=industry_price_list,
    )


