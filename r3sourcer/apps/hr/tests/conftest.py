import datetime

import binascii
import pytest
from django.core.files.base import ContentFile
from django.utils import timezone
from freezegun import freeze_time
from unittest.mock import patch

from r3sourcer.apps.core.models import (
    User, Address, Country, Region, City, Company, CompanyContact, CompanyRel,
    CompanyContactRelationship, InvoiceRule, Invoice, VAT
)
from r3sourcer.apps.hr.models import (
    Jobsite, JobsiteAddress, Vacancy, VacancyDate, Shift, TimeSheet,
    VacancyOffer, CarrierList, BlackList, FavouriteList, TimeSheetIssue,
    PayslipRule
)
from r3sourcer.apps.skills.models import Skill
from r3sourcer.apps.candidate.models import CandidateContact
from r3sourcer.apps.pricing.models import (
    Industry, IndustryPriceList, IndustryPriceListRate, PriceList,
    PriceListRate, RateCoefficient, RateCoefficientModifier, AllowanceWorkRule,
    DynamicCoefficientRule
)


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email='test@test.tt', phone_mobile='+12345678901',
        password='test1234'
    )


@pytest.fixture
def user_another(db):
    return User.objects.create_user(
        email='test2@test.tt', phone_mobile='+12345678902',
        password='test2345'
    )


@pytest.fixture
def contact_data():
    return dict(
        title='Mr.',
        first_name='John',
        last_name='Connor',
        email='test@test.tt',
        phone_mobile='+12345678901'
    )


@pytest.fixture
def contact_data_another():
    return dict(
        title='Ms.',
        first_name='Sarah',
        last_name='Connor',
        email='test2@test.tt',
        phone_mobile='+12345678902'
    )


@pytest.fixture
def contact(db, user, contact_data):
    contact = user.contact
    keys = ('title', 'first_name', 'last_name', 'email', 'phone_mobile')
    for key in keys:
        setattr(contact, key, contact_data[key])
    return contact


@pytest.fixture
def contact_another(db, user_another, contact_data_another):
    contact = user_another.contact
    keys = ('title', 'first_name', 'last_name', 'email', 'phone_mobile')
    for key in keys:
        setattr(contact, key, contact_data_another[key])
    return contact


@pytest.fixture
def candidate_contact(db, contact):
    return CandidateContact.objects.create(
        contact=contact
    )


@pytest.fixture
def candidate_contact_another(db, contact_another):
    return CandidateContact.objects.create(
        contact=contact_another
    )


@pytest.fixture
def company_contact(db, contact):
    return CompanyContact.objects.create(
        contact=contact,
        pin_code='1234'
    )


@pytest.fixture
def company_contact_another(db, contact_another):
    return CompanyContact.objects.create(
        contact=contact_another
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
def industry(db):
    return Industry.objects.create(type='test')


@pytest.fixture
def jobsite(db, master_company, company_contact, industry):
    return Jobsite.objects.create(
        industry=industry,
        master_company=master_company,
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=7),
        primary_contact=company_contact
    )


@pytest.fixture
@patch('r3sourcer.apps.core.models.core.fetch_geo_coord_by_address',
       return_value=(42, 42))
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
def jobsite_address(db, address, jobsite, regular_company):
    return JobsiteAddress.objects.create(
        jobsite=jobsite,
        address=address,
        regular_company=regular_company
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
def vacancy(db, master_company, regular_company, jobsite, skill):
    return Vacancy.objects.create(
        provider_company=master_company,
        customer_company=regular_company,
        jobsite=jobsite,
        position=skill,
        published=True
    )


@pytest.fixture
def vacancy_date(db, vacancy):
    return VacancyDate.objects.create(
        vacancy=vacancy,
        shift_date=datetime.date(2017, 1, 2)
    )


@pytest.fixture
def shift(db, vacancy_date):
    return Shift.objects.create(
        date=vacancy_date,
        time=datetime.time(hour=8, minute=30)
    )


@pytest.fixture
def vacancy_offer(db, shift, candidate_contact):
    return VacancyOffer.objects.create(
        shift=shift,
        candidate_contact=candidate_contact
    )


@pytest.fixture
def vacancy_offer_yesterday(db, vacancy, candidate_contact):
    vacancy_date_yesterday = VacancyDate.objects.create(
        vacancy=vacancy,
        shift_date=datetime.date(2017, 1, 1)
    )
    shift_yesterday = Shift.objects.create(
        date=vacancy_date_yesterday,
        time=datetime.time(hour=8, minute=30)
    )

    return VacancyOffer.objects.create(
        shift=shift_yesterday,
        candidate_contact=candidate_contact,
        status=VacancyOffer.STATUS_CHOICES.accepted
    )


@pytest.fixture
def vacancy_offer_tomorrow(db, vacancy, candidate_contact):
    vacancy_date_tomorrow = VacancyDate.objects.create(
        vacancy=vacancy,
        shift_date=datetime.date(2017, 1, 3)
    )
    shift_tomorrow = Shift.objects.create(
        date=vacancy_date_tomorrow,
        time=datetime.time(hour=8, minute=30)
    )

    return VacancyOffer.objects.create(
        shift=shift_tomorrow,
        candidate_contact=candidate_contact
    )


@pytest.fixture
@freeze_time(datetime.datetime(2017, 1, 1))
def timesheet(db, vacancy_offer, company_contact):
    return TimeSheet.objects.create(
        vacancy_offer=vacancy_offer,
        supervisor=company_contact
    )


@pytest.fixture
@freeze_time(datetime.datetime(2017, 1, 1))
def timesheet_approved(db, vacancy_offer, company_contact):
    return TimeSheet.objects.create(
        vacancy_offer=vacancy_offer,
        supervisor=company_contact,
        supervisor_approved_at=timezone.now(),
        candidate_submitted_at=timezone.now(),
        going_to_work_confirmation=True,
    )


@pytest.fixture
@freeze_time(datetime.datetime(2017, 1, 2))
def timesheet_tomorrow(db, vacancy_offer, company_contact):
    return TimeSheet.objects.create(
        vacancy_offer=vacancy_offer,
        supervisor=company_contact
    )


@pytest.fixture
def timesheet_issue(db, timesheet, company_contact):
    return TimeSheetIssue.objects.create(
        time_sheet=timesheet,
        subject='subject',
        description='description',
        supervisor=company_contact
    )


@pytest.fixture
@freeze_time(datetime.datetime(2017, 1, 1))
def carrier_list(db, candidate_contact, vacancy_offer):
    return CarrierList.objects.create(
        candidate_contact=candidate_contact,
        vacancy_offer=vacancy_offer
    )


@pytest.fixture
def black_list(master_company, candidate_contact):
    return BlackList.objects.create(
        company=master_company,
        candidate_contact=candidate_contact
    )


@pytest.fixture
def favourite_list(company_contact, candidate_contact):
    return FavouriteList.objects.create(
        company_contact=company_contact,
        candidate_contact=candidate_contact
    )


@pytest.fixture
def company_rel(db, master_company, regular_company, company_contact):
    return CompanyRel.objects.create(
        master_company=master_company,
        regular_company=regular_company,
        primary_contact=company_contact
    )


@pytest.fixture
def company_contact_rel(db, regular_company, company_contact):
    return CompanyContactRelationship.objects.create(
        company=regular_company,
        company_contact=company_contact
    )


@pytest.fixture
def picture(faker):
    # See: http://stackoverflow.com/a/30290754
    sequence = binascii.unhexlify(
        'FFD8FFE000104A46494600010101004800480000FFDB004300FFFFFFFFFFFFFFFFFFF'
        'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'
        'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFC2000B080001000101011100FFC'
        '40014100100000000000000000000000000000000FFDA0008010100013F10')
    return ContentFile(bytes(sequence), faker.file_name(extension='jpg'))


@pytest.fixture
def industry_price_list(db, industry):
    return IndustryPriceList.objects.create(
        industry=industry,
    )


@pytest.fixture
def price_list(db, master_company, industry_price_list):
    return PriceList.objects.create(
        company=master_company,
        industry_price_list=industry_price_list,
    )


@pytest.fixture
def price_list_rate(db, price_list, skill):
    return PriceListRate.objects.create(
        price_list=price_list,
        skill=skill,
        hourly_rate=10,
    )


@pytest.fixture
def industry_price_list_rate(db, industry_price_list, skill):
    return IndustryPriceListRate.objects.create(
        industry_price_list=industry_price_list,
        skill=skill,
    )


@pytest.fixture
def invoice_rule_master_company(db, master_company):
    return InvoiceRule.objects.create(
        company=master_company,
    )


@pytest.fixture
def invoice_rule_company(db, regular_company):
    return InvoiceRule.objects.create(
        company=regular_company,
    )


@pytest.fixture
def payslip_rule_master_company(db, master_company):
    return PayslipRule.objects.create(
        company=master_company,
    )


@pytest.fixture
def payslip_rule_company(db, regular_company):
    return PayslipRule.objects.create(
        company=regular_company,
    )


@pytest.fixture
def rate_coefficient(db):
    coeff = RateCoefficient.objects.create(name='test')
    RateCoefficientModifier.objects.create(
        type=RateCoefficientModifier.TYPE_CHOICES.company,
        rate_coefficient=coeff,
        multiplier=2,
    )

    return coeff


@pytest.fixture
def allowance_rate_coefficient(db):
    coeff = RateCoefficient.objects.create(name='test')
    RateCoefficientModifier.objects.create(
        type=RateCoefficientModifier.TYPE_CHOICES.company,
        rate_coefficient=coeff,
        fixed_override=10,
    )
    rule = AllowanceWorkRule.objects.create(allowance_description='Travel')
    DynamicCoefficientRule.objects.create(
        rate_coefficient=coeff,
        rule=rule,
    )

    return coeff


@pytest.fixture
@freeze_time(datetime.datetime(2017, 1, 1))
def invoice(db, master_company, regular_company):
    return Invoice.objects.create(
        provider_company=master_company,
        customer_company=regular_company,
    )


@pytest.fixture
def vat():
    country, _ = Country.objects.get_or_create(name='Australia', code2='AU')
    return VAT.objects.create(
        country=country,
        name='GST',
        rate=0.1,
        start_date=datetime.date(2017, 1, 1),
    )
