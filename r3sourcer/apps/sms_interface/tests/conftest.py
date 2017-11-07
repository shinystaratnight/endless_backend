import pytest

from r3sourcer.apps.core.models import User, Company, CompanyContact
from r3sourcer.apps.sms_interface.models import SMSMessage, SMSTemplate



@pytest.fixture
def user(db):
    return User.objects.create_user(
        email='test@test.tt', phone_mobile='+12345678999',
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
        business_id='111',
        registered_for_gst=True,
        manager=manager,
        type=Company.COMPANY_TYPES.master,
    )


@pytest.fixture
def fake_sms(contact):
    return SMSMessage(
        from_number=contact.phone_mobile,
        to_number='+12345678901',
        text='fake',
        sid='FAKE_test',
    )


@pytest.fixture
def sms_template():
    return SMSTemplate.objects.create(
        name='SMS Template',
        type=SMSTemplate.SMS,
        message_text_template='template'
    )
