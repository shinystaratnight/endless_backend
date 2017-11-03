import datetime

import pytest
from unittest.mock import patch

from django.utils import timezone
from r3sourcer.apps.core.models import User, Address, Country, Region, City, \
    BankAccount, Tag, CompanyContact, Company
from r3sourcer.apps.acceptance_tests.models import (
    AcceptanceTest, AcceptanceTestQuestion, AcceptanceTestAnswer
)
from r3sourcer.apps.skills.models import (
    Skill, EmploymentClassification, SkillBaseRate
)
from r3sourcer.apps.candidate.models import (
    CandidateContact, VisaType, SuperannuationFund, SkillRel, SkillRateRel,
    TagRel, AcceptanceTestRel, CandidateRel
)


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email='test@test.tt', phone_mobile='+12345678901',
        password='test1234'
    )


@pytest.fixture
def contact_data():
    return dict(
        title='Mr.',
        first_name='John',
        last_name='Connor',
        email='connor@test.test',
        phone_mobile='+41789272696'
    )


@pytest.fixture
def contact(db, user, contact_data):
    contact = user.contact
    keys = ('title first_name last_name email phone_mobile').split()
    for key in keys:
        setattr(contact, key, contact_data[key])
    return contact


@pytest.fixture
def employment_classification(db):
    return EmploymentClassification.objects.create(
        name="test"
    )


@pytest.fixture
def bank_account(db, contact):
    return BankAccount.objects.create(
        bank_name="bank name",
        bank_account_name="bank account name",
        bsb="###",
        account_number="987",
        contact=contact,
    )


@pytest.fixture
def candidate_data(employment_classification, bank_account):
    return dict(
        height=178,
        weight=86,
        transportation_to_work=True,
        strength=1,
        language=5,
        reliability_score=1,
        loyalty_score=2,
        tax_file_number="123456",
        super_annual_fund_name="fund name",
        super_member_number="some number",
        bank_account=bank_account,
        emergency_contact_name="emergency name",
        emergency_contact_phone="+41789232323",
        employment_classification=employment_classification
    )


@pytest.fixture
def candidate(db, contact, candidate_data):
    rc = CandidateContact.objects.create(
        contact=contact
    )
    keys = ('height weight transportation_to_work strength language'
            ' reliability_score loyalty_score tax_file_number'
            ' super_annual_fund_name super_member_number bank_account'
            ' emergency_contact_name emergency_contact_phone'
            ' employment_classification').split()
    for key in keys:
        setattr(rc, key, candidate_data[key])
    return rc


@pytest.fixture
def country(db):
    return Country.objects.get_or_create(name='Australia', code2='AU')[0]


@pytest.fixture
@patch('r3sourcer.apps.core.models.core.fetch_geo_coord_by_address',
       return_value=(42, 42))
def address(db, country):
    state = Region.objects.create(name='test', country=country)
    city = City.objects.create(name='city', country=country)
    return Address.objects.create(
        street_address="test street",
        postal_code="123456",
        city=city,
        state=state
    )


@pytest.fixture
def visa_type(db):
    return VisaType.objects.create(
        subclass="1234",
        name="Visa name",
        work_hours_allowed=20,
        is_available=True
    )


@pytest.fixture
def superannuation_fund(db):
    return SuperannuationFund.objects.create(
        name="Test fund",
        membership_number="321"
    )


@pytest.fixture
def skill(db):
    return Skill.objects.create(
        name="Driver",
        carrier_list_reserve=2,
        short_name="Drv",
        active=True
    )


@pytest.fixture
def skill_base_rate(db, skill):
    return SkillBaseRate.objects.create(
        skill=skill,
        hourly_rate=20
    )


@pytest.fixture
def skill_rel(db, skill, candidate):
    return SkillRel.objects.create(
        skill=skill,
        score=4,
        candidate_contact=candidate
    )


@pytest.fixture
def skill_rate_rel(db, skill_rel, skill_base_rate):
    return SkillRateRel.objects.create(
        candidate_skill=skill_rel,
        hourly_rate=skill_base_rate,
        valid_from=timezone.now(),
        valid_until=timezone.now() + datetime.timedelta(days=1)
    )


@pytest.fixture
def tag(db):
    return Tag.objects.create(
        name="Tag name",
        active=True,
        depth=1,
        path="test",
        evidence_required_for_approval=True
    )


@pytest.fixture
def tag_rel(db, tag, candidate):
    return TagRel.objects.create(
        tag=tag,
        candidate_contact=candidate
    )


@pytest.fixture
def company_contact(db, contact):
    return CompanyContact.objects.create(
        contact=contact
    )


@pytest.fixture
def company(db):
    return Company.objects.create(
        name='Company',
        business_id='123',
        registered_for_gst=True,
        type=Company.COMPANY_TYPES.master,
    )


@pytest.fixture
def acceptance_test(db):
    return AcceptanceTest.objects.create(
        test_name='test',
        valid_from=datetime.date(2017, 1, 1),
        valid_until=datetime.date(2018, 1, 1),
        is_active=True
    )


@pytest.fixture
def acceptance_test_rel(db, candidate, acceptance_test):
    return AcceptanceTestRel.objects.create(
        acceptance_test=acceptance_test,
        candidate_contact=candidate
    )


@pytest.fixture
def acceptance_question(db, acceptance_test):
    return AcceptanceTestQuestion.objects.create(
        acceptance_test=acceptance_test,
        question='question'
    )


@pytest.fixture
def acceptance_answer(db, acceptance_question):
    return AcceptanceTestAnswer.objects.create(
        acceptance_test_question=acceptance_question,
        answer='answer',
        order=0,
        is_correct=True
    )


@pytest.fixture
def candidate_rel(db, candidate, company, company_contact):
    return CandidateRel.objects.create(
        candidate_contact=candidate,
        master_company=company,
        company_contact=company_contact
    )
