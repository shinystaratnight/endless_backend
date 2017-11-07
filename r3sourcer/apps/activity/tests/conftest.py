import binascii
import copy
from datetime import datetime
from unittest.mock import patch

import pytest
import pytz
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.utils import timezone
from r3sourcer.apps.core.models import Company, CompanyContact, Contact, User

from r3sourcer.apps.activity.models import (Activity, ActivityDate, ActivityRepeat,
                                     ActivityTemplate)


@pytest.fixture
def activity_template(db):
    return ActivityTemplate.objects.create(
        name='test',
        type=ActivityTemplate.TYPE_CHOICES.ACTIVITY,
        subject_template='text content',
        message_text_template='html content'
    )


@pytest.fixture
def primary_activity(db, activity_template, primary_user):
    return Activity.objects.create(
        template=activity_template,
        contact=primary_user.contact,
        starts_at=timezone.datetime(2017, 1, 1, 12, 0).replace(tzinfo=pytz.UTC),
        ends_at=timezone.datetime(2017, 1, 5, 12, 0).replace(tzinfo=pytz.UTC)
    )


@pytest.fixture
def secondary_activity(db, activity_template, secondary_user):
    return Activity.objects.create(
        template=activity_template,
        contact=secondary_user.contact,
        starts_at=timezone.datetime(2017, 1, 1, 12, 0).replace(tzinfo=pytz.UTC),
        ends_at=timezone.datetime(2017, 1, 5, 12, 0).replace(tzinfo=pytz.UTC)
    )


@pytest.fixture
def activity_repeater(db, faker, primary_activity):
    return ActivityRepeat.objects.create(
        repeat_type=ActivityRepeat.REPEAT_CHOICES.FIXED,
        activity=primary_activity
    )


@pytest.fixture
def repeater_interval1(db, primary_activity):
    return ActivityRepeat.objects.create(
        repeat_type=ActivityRepeat.REPEAT_CHOICES.INTERVAL,
        base_type=ActivityRepeat.PERIODIC_TYPE.secondly,
        every=60,
        activity=primary_activity
    )


@pytest.fixture
def repeater_interval2(db, primary_activity):
    return ActivityRepeat.objects.create(
        repeat_type=ActivityRepeat.REPEAT_CHOICES.SCHEDULE,
        base_type=ActivityRepeat.PERIODIC_TYPE.minutely,
        every=60,
        activity=primary_activity
    )


@pytest.fixture
def repeater_schedule(db, primary_activity):
    return ActivityRepeat.objects.create(
        repeat_type=ActivityRepeat.REPEAT_CHOICES.SCHEDULE,
        base_type=ActivityRepeat.PERIODIC_TYPE.daily,
        hour=10,
        minute=10,
        activity=primary_activity
    )


@pytest.fixture
def activity_date(db, faker, activity_repeater):
    return ActivityDate.objects.create(
        activity_repeat=activity_repeater,
        occur_at=faker.date()
    )


@pytest.fixture
def primary_user(db, faker):
    return User.objects.create_user(
        password=faker.password(),
        email='primary@test.tt', phone_mobile='+12345678921'
    )


@pytest.fixture
def secondary_user(db, faker):
    return User.objects.create_user(
        password=faker.password(),
        email='secondary@test.tt', phone_mobile='+12345678922'
    )


@pytest.fixture
def primary_contact(db, primary_contact_data):
    return Contact.objects.create(**primary_contact_data)


@pytest.fixture
def secondary_contact(db, secondary_contact_data):
    return Contact.objects.create(**secondary_contact_data)


@pytest.fixture
def manager(db, primary_contact):
    return CompanyContact.objects.create(contact=primary_contact)


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
def primary_contact_data(faker, picture):
    return dict(
        title='Mr.',
        # user=primary_user,
        first_name=faker.first_name(),
        last_name=faker.last_name(),
        email=faker.email(),
        phone_mobile='+41789272696',
        gender=Contact._meta.get_field('gender').choices[0][0],
        marital_status=Contact.MARITAL_STATUS_CHOICES.Single,
        birthday=faker.date_time_this_year().date(),
        spouse_name=faker.name(),
        children=0,
        is_available=faker.boolean(),
        picture=copy.deepcopy(picture),
    )


@pytest.fixture
def secondary_contact_data(faker, picture):
    return dict(
        title='Mr.',
        first_name=faker.first_name(),
        last_name=faker.last_name(),
        email=faker.email(),
        phone_mobile='+41789272697',
        gender=Contact._meta.get_field('gender').choices[0][0],
        marital_status=Contact.MARITAL_STATUS_CHOICES.Single,
        birthday=faker.date_time_this_year().date(),
        spouse_name=faker.name(),
        children=0,
        is_available=faker.boolean(),
        picture=copy.deepcopy(picture),
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
