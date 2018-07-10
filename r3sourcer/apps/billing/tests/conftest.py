import datetime

import pytest

from unittest.mock import patch

from r3sourcer.apps.core.models import User, Company, CompanyContact, CompanyContactRelationship, Country, Region, City, Address
from r3sourcer.apps.hr.models import Shift, ShiftDate, Job, Jobsite
from r3sourcer.apps.skills.models import Skill
from r3sourcer.apps.pricing.models import Industry
from r3sourcer.apps.billing.models import Payment, Subscription


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email='test@test.tt', phone_mobile='+12345678901',
        password='test1234'
    )


@pytest.fixture
def contact(db, user):
    return user.contact


@pytest.fixture
def manager(db, contact):
    return CompanyContact.objects.create(contact=contact)


@pytest.fixture
def company(db, manager):
    return Company.objects.create(
        name='Company',
        business_id='123',
        registered_for_gst=True,
        type=Company.COMPANY_TYPES.master,
        manager=manager
    )


@pytest.fixture
def relationship(db, company, manager):
    return CompanyContactRelationship.objects.create(
        company_contact=manager,
        company=company,
    )


@pytest.fixture
def master_company(db):
    return Company.objects.create(
        name='Master',
        business_id='123',
        registered_for_gst=True,
        type=Company.COMPANY_TYPES.master,
        timesheet_approval_scheme=Company.TIMESHEET_APPROVAL_SCHEME.PIN
    )


@pytest.fixture
def regular_company(db):
    return Company.objects.create(
        name='Regular',
        business_id='321',
        registered_for_gst=True,
        type=Company.COMPANY_TYPES.regular
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
def company_contact(db, contact):
    return CompanyContact.objects.create(
        contact=contact,
        pin_code='1234'
    )


@pytest.fixture
def industry(db):
    return Industry.objects.create(type='test')


@pytest.fixture
@patch('r3sourcer.apps.core.models.core.fetch_geo_coord_by_address', return_value=(42, 42))
def address(db):
    country, _ = Country.objects.get_or_create(name='Australia', code2='AU')
    state = Region.objects.create(name='test', country=country)
    city = City.objects.create(name='city', country=country)
    return Address.objects.create(
        street_address="test street",
        postal_code="123456",
        city=city,
        state=state
    )


@pytest.fixture
def jobsite(db, master_company, company_contact, industry, address, regular_company):
    return Jobsite.objects.create(
        industry=industry,
        master_company=master_company,
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=7),
        primary_contact=company_contact,
        address=address,
        regular_company=regular_company,
    )


@pytest.fixture
def job(db, master_company, regular_company, jobsite, skill):
    return Job.objects.create(
        provider_company=master_company,
        customer_company=regular_company,
        jobsite=jobsite,
        position=skill,
        published=True
    )


@pytest.fixture
def shift_date(db, job):
    return ShiftDate.objects.create(
        job=job,
        shift_date=datetime.date.today()
    )


@pytest.fixture
def shift(db, shift_date):
    return Shift.objects.create(
        date=shift_date,
        time=datetime.time(hour=8, minute=30)
    )


@pytest.fixture
def payment(db, company):
    return Payment.objects.create(
        company=company,
        type=Payment.PAYMENT_TYPES.sms,
        amount=100,
        status='done',
        stripe_id='stripeid'
    )


@pytest.fixture
def subscription(db, company):
    return Subscription.objects.create(
        company=company,
        name='Subscription',
        type='monthly',
        price=100,
        worker_count=10,
        status='active',
    )
