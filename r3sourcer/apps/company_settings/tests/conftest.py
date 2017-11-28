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
def group(db):
    return Group.objects.create(name='test_group')


@pytest.fixture
def group_with_permissions(db, group):
    permission = GlobalPermission.objects.create(name='permission_name', codename='permission_codename')
    permission2 = GlobalPermission.objects.create(name='permission_name2', codename='permission_codename2')
    group.permissions.add(permission, permission2)
    return group


@pytest.fixture
def permission_get(db):
    return GlobalPermission.objects.create(name='permission_get', codename='permission_get')


@pytest.fixture
def permission_post(db):
    return GlobalPermission.objects.create(name='permission_post', codename='permission_post')


@pytest.fixture
def permission_patch(db):
    return GlobalPermission.objects.create(name='permission_patch', codename='permission_patch')


@pytest.fixture
def permission_delete(db):
    return GlobalPermission.objects.create(name='permission_delete', codename='permission_delete')


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


@pytest.fixture
def myob_account(db):
    return MYOBAccount.objects.create(
        number='2-2000',
        name='Test Income Account',
        type='income'
    )
