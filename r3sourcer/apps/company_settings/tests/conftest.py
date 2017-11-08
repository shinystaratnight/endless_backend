import pytest

from r3sourcer.apps.core.models import User, Company, CompanyContact, InvoiceRule
from r3sourcer.apps.hr.models import PayslipRule


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
def payslip_rule(db, company):
    return PayslipRule.objects.create(
        company=company,
        comment='comment',
    )


@pytest.fixture
def invoice_rule(db, company):
    return InvoiceRule.objects.create(
        company=company,
        serial_number='TEST',
        starting_number=100,
        comment='comment',
        notice='notice'
    )
