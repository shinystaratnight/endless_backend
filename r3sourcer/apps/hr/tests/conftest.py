import datetime

import binascii
import pytest
from django.core.files.base import ContentFile
from django.utils import timezone
from freezegun import freeze_time
from unittest.mock import patch

from r3sourcer.apps.candidate import models as candidate_models
from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.hr import models as hr_models
from r3sourcer.apps.skills.models import Skill, SkillName
from r3sourcer.apps.pricing import models as pricing_models
from r3sourcer.apps.sms_interface import models as sms_models
from r3sourcer.helpers.datetimes import utc_now


@pytest.fixture
def user(db):
    return core_models.User.objects.create_user(
        email='test@test.tt', phone_mobile='+12345678901',
        password='test1234'
    )


@pytest.fixture
def user_another(db):
    return core_models.User.objects.create_user(
        email='test2@test.tt', phone_mobile='+12345678902',
        password='test2345'
    )


@pytest.fixture
def user_primary(db):
    return core_models.User.objects.create_user(
        email='test3@test.tt', phone_mobile='+12345678903',
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
def contact_primary(db, user_primary):
    return user_primary.contact


@pytest.fixture
def candidate_contact(db, contact):
    return candidate_models.CandidateContact.objects.create(
        contact=contact
    )


@pytest.fixture
def company_contact(db, contact):
    return core_models.CompanyContact.objects.create(
        contact=contact,
        pin_code='1234'
    )


@pytest.fixture
def company_contact_another(db, contact_another):
    return core_models.CompanyContact.objects.create(
        contact=contact_another
    )


@pytest.fixture
def company_contact_primary(db, contact_primary):
    return core_models.CompanyContact.objects.create(
        contact=contact_primary
    )


@pytest.fixture
def master_company(db, company_contact_primary):
    return core_models.Company.objects.create(
        name='Master',
        business_id='123',
        registered_for_gst=True,
        type=core_models.Company.COMPANY_TYPES.master,
        timesheet_approval_scheme=core_models.Company.TIMESHEET_APPROVAL_SCHEME.PIN,
        primary_contact=company_contact_primary
    )


@pytest.fixture
def regular_company(db):
    return core_models.Company.objects.create(
        name='Regular',
        business_id='321',
        registered_for_gst=True,
        type=core_models.Company.COMPANY_TYPES.regular
    )


@pytest.fixture
def industry(db):
    return pricing_models.Industry.objects.create(type='test')


@pytest.fixture
def jobsite(db, master_company, company_contact, industry, address, regular_company):
    return hr_models.Jobsite.objects.create(
        industry=industry,
        master_company=master_company,
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=7),
        primary_contact=company_contact,
        address=address,
        regular_company=regular_company,
    )


@pytest.fixture
@patch('r3sourcer.apps.core.models.core.fetch_geo_coord_by_address',
       return_value=(42, 42))
def address(db):
    country, _ = core_models.Country.objects.get_or_create(name='Australia', code2='AU')
    state = core_models.Region.objects.create(name='test', country=country)
    city = core_models.City.objects.create(name='city', country=country)
    return core_models.Address.objects.create(
        street_address="test street",
        postal_code="123456",
        city=city,
        state=state
    )


@pytest.fixture
def skill_name(db, industry):
    return SkillName.objects.create(name="Driver", industry=industry)


@pytest.fixture
def skill(db, skill_name, master_company):
    return Skill.objects.create(
        name=skill_name,
        carrier_list_reserve=2,
        short_name="Drv",
        active=False,
        company=master_company
    )


@pytest.fixture
def job(db, master_company, regular_company, jobsite, skill):
    return hr_models.Job.objects.create(
        provider_company=master_company,
        customer_company=regular_company,
        jobsite=jobsite,
        position=skill,
        published=True
    )


@pytest.fixture
def shift_date(db, job):
    return hr_models.ShiftDate.objects.create(
        job=job,
        shift_date=datetime.date(2017, 1, 2)
    )


@pytest.fixture
def shift(db, shift_date):
    return hr_models.Shift.objects.create(
        date=shift_date,
        time=datetime.time(hour=8, minute=30)
    )


@pytest.fixture
@patch.object(hr_models.JobOffer, 'check_job_quota', return_value=True)
def job_offer(mock_check, db, shift, candidate_contact):
    job_offer = hr_models.JobOffer.objects.create(
        shift=shift,
        candidate_contact=candidate_contact
    )

    hr_models.JobOfferSMS.objects.create(job_offer=job_offer, offer_sent_by_sms=None)

    return job_offer


@pytest.fixture
@patch.object(hr_models.JobOffer, 'check_job_quota', return_value=True)
def accepted_jo(mock_check, db, shift, candidate_contact):
    return hr_models.JobOffer.objects.create(
        shift=shift,
        candidate_contact=candidate_contact,
        status=hr_models.JobOffer.STATUS_CHOICES.accepted
    )


@pytest.fixture
@patch.object(hr_models.JobOffer, 'check_job_quota', return_value=True)
def cancelled_jo(mock_check, db, shift, candidate_contact):
    return hr_models.JobOffer.objects.create(
        shift=shift,
        candidate_contact=candidate_contact,
        status=hr_models.JobOffer.STATUS_CHOICES.cancelled
    )


@pytest.fixture
@patch.object(hr_models.JobOffer, 'check_job_quota', return_value=True)
def job_offer_yesterday(mock_check, db, job, candidate_contact):
    shift_date_yesterday = hr_models.ShiftDate.objects.create(
        job=job,
        shift_date=datetime.date(2017, 1, 1)
    )
    shift_yesterday = hr_models.Shift.objects.create(
        date=shift_date_yesterday,
        time=datetime.time(hour=8, minute=30)
    )

    return hr_models.JobOffer.objects.create(
        shift=shift_yesterday,
        candidate_contact=candidate_contact,
        status=hr_models.JobOffer.STATUS_CHOICES.accepted
    )


@pytest.fixture
@patch.object(hr_models.JobOffer, 'check_job_quota', return_value=True)
def job_offer_tomorrow(mock_check, db, job, candidate_contact):
    shift_date_tomorrow = hr_models.ShiftDate.objects.create(
        job=job,
        shift_date=datetime.date(2017, 1, 3)
    )
    shift_tomorrow = hr_models.Shift.objects.create(
        date=shift_date_tomorrow,
        time=datetime.time(hour=8, minute=30)
    )

    return hr_models.JobOffer.objects.create(
        shift=shift_tomorrow,
        candidate_contact=candidate_contact
    )


@pytest.fixture
@patch.object(hr_models.JobOffer, 'check_job_quota', return_value=True)
def job_offer_tomorrow_night(mock_check, db, job, candidate_contact):
    shift_date_tomorrow = hr_models.ShiftDate.objects.create(
        job=job,
        shift_date=datetime.date(2017, 1, 3)
    )
    shift_tomorrow = hr_models.Shift.objects.create(
        date=shift_date_tomorrow,
        time=datetime.time(hour=19, minute=0)
    )

    return hr_models.JobOffer.objects.create(
        shift=shift_tomorrow,
        candidate_contact=candidate_contact
    )


@pytest.fixture
@freeze_time(datetime.datetime(2017, 1, 1))
def timesheet(db, job_offer, company_contact):
    return hr_models.TimeSheet.objects.create(
        job_offer=job_offer,
        supervisor=company_contact
    )


@pytest.fixture
@freeze_time(datetime.datetime(2017, 1, 1))
def timesheet_approved(db, job_offer, company_contact):
    return hr_models.TimeSheet.objects.create(
        job_offer=job_offer,
        supervisor=company_contact,
        supervisor_approved_at=timezone.now(),
        candidate_submitted_at=timezone.now(),
        going_to_work_confirmation=True,
    )


@pytest.fixture
@freeze_time(datetime.datetime(2017, 1, 2))
def timesheet_tomorrow(db, job_offer, company_contact):
    return hr_models.TimeSheet.objects.create(
        job_offer=job_offer,
        supervisor=company_contact
    )


@pytest.fixture
def timesheet_issue(db, timesheet, company_contact):
    return hr_models.TimeSheetIssue.objects.create(
        time_sheet=timesheet,
        subject='subject',
        description='description',
        supervisor=company_contact
    )


@pytest.fixture
@freeze_time(datetime.datetime(2017, 1, 2))
def timesheet_with_break(db, job_offer, company_contact):
    return hr_models.TimeSheet.objects.create(
        job_offer=job_offer,
        supervisor=company_contact,
        shift_started_at=utc_now().replace(hour=8, minute=0),
        shift_ended_at=utc_now().replace(hour=8, minute=0) + datetime.timedelta(hours=8),
        break_started_at=utc_now().replace(hour=8, minute=0) + datetime.timedelta(hours=4),
        break_ended_at=utc_now().replace(hour=8, minute=0) + datetime.timedelta(hours=4, minutes=30),
    )


@pytest.fixture
@freeze_time(datetime.datetime(2017, 1, 1))
def carrier_list(db, candidate_contact, job_offer):
    return hr_models.CarrierList.objects.create(
        candidate_contact=candidate_contact,
        job_offer=job_offer
    )


@pytest.fixture
def black_list(master_company, candidate_contact):
    return hr_models.BlackList.objects.create(
        company=master_company,
        candidate_contact=candidate_contact
    )


@pytest.fixture
def favourite_list(company_contact, candidate_contact):
    return hr_models.FavouriteList.objects.create(
        company_contact=company_contact,
        candidate_contact=candidate_contact
    )


@pytest.fixture
def company_rel(db, master_company, regular_company, company_contact):
    return core_models.CompanyRel.objects.create(
        master_company=master_company,
        regular_company=regular_company,
        manager=company_contact
    )


@pytest.fixture
def company_contact_rel(db, regular_company, company_contact):
    return core_models.CompanyContactRelationship.objects.create(
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
def price_list(db, master_company):
    return pricing_models.PriceList.objects.create(
        company=master_company,
        valid_from=timezone.datetime(2017, 1, 1, 12, 0)
    )


@pytest.fixture
def price_list_rate(db, price_list, skill):
    return pricing_models.PriceListRate.objects.create(
        price_list=price_list,
        skill=skill,
        hourly_rate=10,
    )


@pytest.fixture
def invoice_rule_master_company(db, master_company):
    return core_models.InvoiceRule.objects.create(
        company=master_company,
    )


@pytest.fixture
def invoice_rule_company(db, regular_company):
    return core_models.InvoiceRule.objects.create(
        company=regular_company,
    )


@pytest.fixture
def payslip_rule_master_company(db, master_company):
    return hr_models.PayslipRule.objects.create(
        company=master_company,
    )


@pytest.fixture
def payslip_rule_company(db, regular_company):
    return hr_models.PayslipRule.objects.create(
        company=regular_company,
    )


@pytest.fixture
def rate_coefficient(db, industry):
    coeff = pricing_models.RateCoefficient.objects.create(name='test', industry=industry)
    pricing_models.RateCoefficientModifier.objects.create(
        type=pricing_models.RateCoefficientModifier.TYPE_CHOICES.company,
        rate_coefficient=coeff,
        multiplier=2,
    )

    return coeff


@pytest.fixture
def allowance_rate_coefficient(db, industry):
    coeff = pricing_models.RateCoefficient.objects.create(name='test', industry=industry)
    pricing_models.RateCoefficientModifier.objects.create(
        type=pricing_models.RateCoefficientModifier.TYPE_CHOICES.company,
        rate_coefficient=coeff,
        fixed_override=10,
    )
    rule = pricing_models.AllowanceWorkRule.objects.create(allowance_description='Travel')
    pricing_models.DynamicCoefficientRule.objects.create(
        rate_coefficient=coeff,
        rule=rule,
    )

    return coeff


@pytest.fixture
@freeze_time(datetime.datetime(2017, 1, 1))
def invoice(db, master_company, regular_company):
    return core_models.Invoice.objects.create(
        provider_company=master_company,
        customer_company=regular_company,
    )


@pytest.fixture
def vat():
    country, _ = core_models.Country.objects.get_or_create(name='Australia', code2='AU')
    return core_models.VAT.objects.get_or_create(
        country=country,
        name='GST',
        defaults={
            'rate': 0.1,
            'start_date': datetime.date(2017, 1, 1),
        }
    )[0]


@pytest.fixture
def fake_sms(contact):
    return sms_models.SMSMessage.objects.create(
        from_number=contact.phone_mobile,
        to_number='+12345678901',
        text='fake',
        sid='FAKE_test',
    )
