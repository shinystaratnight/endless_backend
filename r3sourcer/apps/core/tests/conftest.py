import binascii
import copy
import pytest

from unittest.mock import patch
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.files.base import ContentFile

from r3sourcer.apps.candidate.models import CandidateContact, CandidateRel
from r3sourcer.apps.core import models


@pytest.fixture
def user(db):
    return models.User.objects.create_user(
        email='test@test.tt', phone_mobile='+12345678901',
        password='test1234'
    )


@pytest.fixture
def secondary_user(db, faker):
    return models.User.objects.create_user(
        password=faker.password(),
        email='secondary@test.tt', phone_mobile='+12345678922'
    )


@pytest.fixture
def primary_user(db):
    return models.User.objects.create_user(
        email='primary@test.tt', phone_mobile='+12345678921',
        password='primary1234'
    )


@pytest.fixture
def staff_user(db):
    return models.User.objects.create_user(
        email='staff@test.tt', phone_mobile='+12345123451',
        password='staff-user'
    )


@pytest.fixture
def superuser(db):
    return models.User.objects.create_superuser(
        email='test@test.tt', phone_mobile='+12345678901',
        password='test1234'
    )


@pytest.fixture
@patch('r3sourcer.apps.core.models.core.fetch_geo_coord_by_address', return_value=(42, 42))
def addresses(mock_fetch, db):
    country = models.Country.objects.get(code2='AU')
    state = models.Region.objects.create(name='test', country=country)
    city = models.City.objects.create(name='city', country=country)
    return [
        models.Address.objects.create(
            street_address='street%d' % i, city=city,
            postal_code='111%d' % i,
            state=state, country=country
        ) for i in range(4)
    ]


@pytest.fixture
def address(db, addresses):
    return addresses[0]


@pytest.fixture
def contact_address(db, addresses):
    return addresses[3]


@pytest.fixture
def contact(db, user, contact_data, contact_address):
    contact = user.contact
    keys = (
        'title', 'first_name', 'password', 'last_name', 'email', 'gender',
        'phone_mobile', 'marital_status', 'birthday', 'spouse_name', 'children'
    )
    for key in keys:
        setattr(contact, key, contact_data[key])
    contact.address = contact_address
    contact.save()
    return contact


@pytest.fixture
def manager(db, contact):
    return models.CompanyContact.objects.create(contact=contact)


@pytest.fixture
def primary_company_contact(db, primary_user):
    return models.CompanyContact.objects.create(contact=primary_user.contact)


@pytest.fixture
def staff_company_contact(db, staff_user):
    return models.CompanyContact.objects.create(contact=staff_user.contact)


@pytest.fixture
def company_other(db, manager, addresses):
    comp = models.Company.objects.create(
        name='Company',
        business_id='111',
        registered_for_gst=True,
        manager=manager,
        type=models.Company.COMPANY_TYPES.master,
    )

    models.CompanyAddress.objects.create(
        company=comp,
        address=addresses[1],
        name='Test',
    )

    return comp


@pytest.fixture
def company_regular(db, manager):
    return models.Company.objects.create(
        name='Company regular',
        business_id='222',
        registered_for_gst=True,
        manager=manager,
        type=models.Company.COMPANY_TYPES.regular,
    )


@pytest.fixture
def company_address_regular(db, manager, addresses, company_regular):
    return models.CompanyAddress.objects.create(
        company=company_regular,
        address=addresses[1],
        name='Test regular',
    )


@pytest.fixture
def company(db, manager):
    return models.Company.objects.create(
        name='Company',
        business_id='111',
        registered_for_gst=True,
        manager=manager,
        type=models.Company.COMPANY_TYPES.master,
    )


@pytest.fixture
def company_address(db, manager, addresses, company):
    return models.CompanyAddress.objects.create(
        company=company,
        address=addresses[2],
        name='Test',
    )


@pytest.fixture
def workflow_ct(db):
    obj, _ = ContentType.objects.get_or_create(
        app_label="core",
        model="workflowprocess"
    )
    return obj


def prefill_workflow():
    company = models.Company.objects.create(
        name='New C',
        business_id='123',
        registered_for_gst=True,
        type=models.Company.COMPANY_TYPES.master,
    )
    content_type, created = ContentType.objects.get_or_create(app_label="core", model="workflowprocess")
    workflow, created = models.Workflow.objects.get_or_create(name="test_workflow", model=content_type)
    data = [
        {"active": [0], "required_states": ["and", 40]},
        {"active": [10], "required_states": None},
        {"active": [10, 20], "required_states": ['and', 10]},
        {"active": [30], "required_states": ["and", 10, 20], "required_functions": ["and", "is_test_function"]},
        {"active": [30, 40], "required_states": ["or", 20, 30]},
        {"active": [40, 50], "required_states": ["and", 30, 40]},
        {"active": [60], "required_states": ["or", 40, 50]},
        {"active": [70], },
        {"active": [80], "required_states": ["and", 30], "actions": ["content_type"]},
        {"active": [90], "required_states": ["and", 30], "actions": ["test"]},
        {"active": [10, 20, 100], },
        {"required_states": ["and", 30]},
        {},
    ]

    counter = 0
    for rule in data:
        models.WorkflowNode.objects.get_or_create(number=counter * 10,
                                                  name_before_activation="State " + str(counter * 10),
                                                  workflow=workflow, company=company,
                                                  rules=rule, hardlock=True)
        counter += 1


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('cities_light_curr', '--force-import-all')
        call_command('loaddata', 'company_localization.json')
        prefill_workflow()


@pytest.fixture
def company_rel(db, company, company_regular, primary_company_contact):
    return models.CompanyRel.objects.create(
        master_company=company,
        regular_company=company_regular,
        primary_contact=primary_company_contact
    )


@pytest.fixture
def staff_relationship(db, staff_company_contact, company):
    return models.CompanyContactRelationship.objects.create(
        company_contact=staff_company_contact,
        company=company,
    )


@pytest.fixture
def picture(faker):
    # See: http://stackoverflow.com/a/30290754
    sequence = binascii.unhexlify(
        'FFD8FFE000104A46494600010101004800480000FFDB004300FFFFFFFFFFFFFFFFFFFF'
        'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'
        'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFC2000B080001000101011100FFC400'
        '14100100000000000000000000000000000000FFDA0008010100013F10')
    return ContentFile(bytes(sequence), faker.file_name(extension='jpg'))


@pytest.fixture
def contact_phone():
    return '+41789272696'


@pytest.fixture
def contact_data(faker, contact_phone, picture):
    return dict(
        title='Mr.',
        first_name=faker.first_name(),
        password=faker.password(),
        last_name=faker.last_name(),
        email=faker.email(),
        phone_mobile=contact_phone,
        gender=models.Contact._meta.get_field('gender').choices[0][0],
        marital_status=models.Contact.MARITAL_STATUS_CHOICES.Single,
        birthday=faker.date_time_this_year().date(),
        spouse_name=faker.name(),
        children=0,
        is_available=faker.boolean(),
        picture=copy.deepcopy(picture),
    )


@pytest.fixture
def order(db, company, manager):
    customer_company = models.Company.objects.create(
        name='CustomerCompany',
        business_id='222',
        registered_for_gst=True,
        manager=manager
    )

    return models.Order.objects.create(customer_company=customer_company, provider_company=company)


@pytest.fixture
def country(db):
    return models.Country.objects.get(code2='AU')


@pytest.fixture
def city(db, country):
    return models.City.objects.filter(country=country).order_by('name').first()


@pytest.fixture
def region(db, city):
    return models.Region.objects.get(pk=city.region.pk)


@pytest.fixture
def invoice(db, company, company_regular):
    return models.Invoice.objects.create(
        provider_company=company,
        customer_company=company_regular,
        total_with_tax=20,
        total=15,
        tax=5,
        myob_number='test'
    )


@pytest.fixture
def invoice_rule(db, company):
    return models.InvoiceRule.objects.create(
        company=company,
        serial_number='TEST',
        starting_number=100,
        comment='comment',
        notice='notice'
    )


@pytest.fixture
def site(db):
    return Site.objects.create(
        domain='test.tt',
        name='Test'
    )


@pytest.fixture
def site_company(db, site, company):
    return models.SiteCompany.objects.create(
        company=company,
        site=site
    )


@pytest.fixture
def site_regular_company(db, site, company_regular):
    return models.SiteCompany.objects.create(
        company=company_regular,
        site=site
    )


@pytest.fixture
def dashboard_modules(db):
    return models.DashboardModule.objects.bulk_create([
        models.DashboardModule(
            content_type=ContentType.objects.get_for_model(models.CompanyContact),
            is_active=True
        ),
        models.DashboardModule(
            content_type=ContentType.objects.get_for_model(models.CompanyAddress),
            is_active=True
        ),
        models.DashboardModule(
            content_type=ContentType.objects.get_for_model(models.Company),
            is_active=True
        ),
        models.DashboardModule(
            content_type=ContentType.objects.get_for_model(models.SiteCompany),
            is_active=False
        ),
    ])


@pytest.fixture
def company_contact(db, contact):
    return models.CompanyContact.objects.create(
        contact=contact
    )


@pytest.fixture
def user_dashboard_module(db, dashboard_modules, company_contact):
    return models.UserDashboardModule.objects.create(
        company_contact=company_contact,
        dashboard_module=dashboard_modules[0],
        position=0
    )


@pytest.fixture
def candidate_contact(db, contact):
    return CandidateContact.objects.create(
        contact=contact
    )


@pytest.fixture
def candidate_rel(db, candidate_contact, company, company_contact):
    return CandidateRel.objects.create(
        candidate_contact=candidate_contact,
        master_company=company,
        company_contact=company_contact,
    )
