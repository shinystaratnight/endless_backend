import datetime
import pytz

import pytest
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from r3sourcer.apps.acceptance_tests import models as acceptance_test_models
from r3sourcer.apps.activity import models as activity_models
from r3sourcer.apps.candidate import models as candidate_models
from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.pricing.models import PriceList, Industry
from r3sourcer.apps.skills import models as skills_models


@pytest.fixture
def user(db):
    return core_models.User.objects.create_user(
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
    return skills_models.EmploymentClassification.objects.create(
        name="test"
    )


@pytest.fixture
def bank_account(db, contact):
    return core_models.BankAccount.objects.create(
        bank_name="bank name",
        bank_account_name="bank account name",
        bsb="###",
        account_number="987",
        contact=contact,
    )


@pytest.fixture
def candidate_data(employment_classification, bank_account, superannuation_fund):
    return dict(
        height=178,
        weight=86,
        transportation_to_work=True,
        strength=1,
        language=5,
        tax_file_number="123456",
        super_annual_fund_name="fund name",
        super_member_number="some number",
        bank_account=bank_account,
        emergency_contact_name="emergency name",
        emergency_contact_phone="+41789232323",
        employment_classification=employment_classification,
        superannuation_fund=superannuation_fund,
    )


@pytest.fixture
def candidate(db, contact, candidate_data):
    rc = candidate_models.CandidateContact.objects.create(
        contact=contact
    )

    rc.candidate_scores.reliability = 1
    rc.candidate_scores.loyalty = 2
    rc.candidate_scores.save(update_fields=['reliability', 'loyalty'])

    keys = [
        'height', 'weight', 'transportation_to_work', 'strength', 'language', 'tax_file_number', 'superannuation_fund',
        'super_member_number', 'bank_account', 'emergency_contact_name', 'emergency_contact_phone',
        'employment_classification'
    ]
    for key in keys:
        setattr(rc, key, candidate_data[key])
    return rc


@pytest.fixture
def country(db):
    return core_models.Country.objects.get_or_create(name='Australia', code2='AU')[0]


@pytest.fixture
@patch('r3sourcer.apps.core.models.core.fetch_geo_coord_by_address',
       return_value=(42, 42))
def address(db, country):
    state = core_models.Region.objects.create(name='test', country=country)
    city = core_models.City.objects.create(name='city', country=country)
    return core_models.Address.objects.create(
        street_address="test street",
        postal_code="123456",
        city=city,
        state=state
    )


@pytest.fixture
def visa_type(db):
    return candidate_models.VisaType.objects.create(
        subclass="1234",
        name="Visa name",
        work_hours_allowed=20,
        is_available=True
    )


@pytest.fixture
def superannuation_fund(db):
    return candidate_models.SuperannuationFund.objects.create(
        name="Test fund",
        membership_number="321"
    )


@pytest.fixture
def skill(db):
    return skills_models.Skill.objects.create(
        name="Driver",
        carrier_list_reserve=2,
        short_name="Drv",
        active=False
    )


@pytest.fixture
def skill_base_rate(db, skill):
    return skills_models.SkillBaseRate.objects.create(
        skill=skill,
        hourly_rate=20
    )


@pytest.fixture
def skill_rel(db, skill, candidate):
    return candidate_models.SkillRel.objects.create(
        skill=skill,
        score=4,
        candidate_contact=candidate
    )


@pytest.fixture
def skill_rate_rel(db, skill_rel, skill_base_rate):
    return candidate_models.SkillRateRel.objects.create(
        candidate_skill=skill_rel,
        hourly_rate=skill_base_rate,
        valid_from=timezone.now(),
        valid_until=timezone.now() + datetime.timedelta(days=1)
    )


@pytest.fixture
def tag(db):
    return core_models.Tag.objects.create(
        name="Tag name",
        active=True,
        evidence_required_for_approval=True
    )


@pytest.fixture
def tag_rel(db, tag, candidate):
    return candidate_models.TagRel.objects.create(
        tag=tag,
        candidate_contact=candidate
    )


@pytest.fixture
def company_contact(db, contact):
    return core_models.CompanyContact.objects.create(
        contact=contact
    )


@pytest.fixture
def company(db):
    return core_models.Company.objects.create(
        name='Company',
        business_id='123',
        registered_for_gst=True,
        type=core_models.Company.COMPANY_TYPES.master,
    )


@pytest.fixture
def acceptance_test(db):
    return acceptance_test_models.AcceptanceTest.objects.create(
        test_name='test',
        valid_from=datetime.date(2017, 1, 1),
        valid_until=datetime.date(2018, 1, 1),
        is_active=True
    )


@pytest.fixture
def acceptance_test_rel(db, candidate, acceptance_test):
    return candidate_models.AcceptanceTestRel.objects.create(
        acceptance_test=acceptance_test,
        candidate_contact=candidate
    )


@pytest.fixture
def acceptance_question(db, acceptance_test):
    return acceptance_test_models.AcceptanceTestQuestion.objects.create(
        acceptance_test=acceptance_test,
        question='question'
    )


@pytest.fixture
def acceptance_answer(db, acceptance_question):
    return acceptance_test_models.AcceptanceTestAnswer.objects.create(
        acceptance_test_question=acceptance_question,
        answer='answer',
        order=0,
        is_correct=True
    )


@pytest.fixture
def candidate_rel(db, candidate, company, company_contact):
    return candidate_models.CandidateRel.objects.create(
        candidate_contact=candidate,
        master_company=company,
        company_contact=company_contact
    )


@pytest.fixture
def candidate_note(db, candidate):
    return core_models.Note.objects.create(
        object=candidate,
        note='note'
    )


@pytest.fixture
def activity_template(db):
    return activity_models.ActivityTemplate.objects.create(
        name='test',
        type=activity_models.ActivityTemplate.TYPE_CHOICES.ACTIVITY,
        subject_template='text content',
        message_text_template='html content'
    )


@pytest.fixture
def candidate_activity(db, candidate, contact, activity_template):
    return activity_models.Activity.objects.create(
        entity_object_id=candidate.id,
        entity_object_name=candidate_models.CandidateContact.__name__,
        contact=contact,
        starts_at=timezone.datetime(2017, 1, 1, 12, 0).replace(tzinfo=pytz.UTC),
        ends_at=timezone.datetime(2017, 1, 5, 12, 0).replace(tzinfo=pytz.UTC),
        template=activity_template
    )


@pytest.fixture
def workflow_state(db, candidate, company):
    content_type = ContentType.objects.get_for_model(candidate_models.CandidateContact)
    workflow, created = core_models.Workflow.objects.get_or_create(name="test_workflow", model=content_type)
    return core_models.WorkflowNode.objects.create(
        number=11, name_before_activation="State 11", workflow=workflow, company=company, rules={}
    )


@pytest.fixture
def industry(db):
    return Industry.objects.create(type='test')


@pytest.fixture
def price_list(db, company):
    return PriceList.objects.create(
        company=company,
    )
