import pytest

from django.contrib.auth.models import Group

from r3sourcer.apps.company_settings.models import MYOBAccount
from r3sourcer.apps.core.models import User, Company, CompanyContact, InvoiceRule
from r3sourcer.apps.hr.models import PayslipRule
from r3sourcer.apps.company_settings.models import GlobalPermission
from r3sourcer.apps.core.models import User, Company, CompanyContact


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
(??)


@pytest.fixture
(??)


@pytest.fixture
(??)
