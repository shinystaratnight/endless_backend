import pytest

from r3sourcer.apps.core.models import User, Company, CompanyContact, CompanyContactRelationship


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
