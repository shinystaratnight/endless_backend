from datetime import datetime

from django.utils import timezone

import freezegun
import pytest

from r3sourcer.apps.email_interface import models


@pytest.fixture
def email_template():
    return models.EmailTemplate.objects.create(
        name='Email Template',
        type=models.EmailTemplate.EMAIL,
        message_text_template='template',
        subject_template='subject'
    )


@pytest.fixture
@freezegun.freeze_time(datetime(2017, 1, 1))
def fake_email():
    return models.EmailMessage.objects.create(
        state=models.EmailMessage.STATE_CHOICES.CREATED,
        sent_at=timezone.now(),
        from_email='test@test.tt',
        subject='subject',
        created_at=timezone.now(),
        to_addresses='test1@test.tt'
    )


@pytest.fixture
def fake_email_text_body(fake_email):
    return models.EmailBody.objects.create(
        content='test',
        message=fake_email
    )


@pytest.fixture
def fake_email_html_body(fake_email):
    return models.EmailBody.objects.create(
        content='test',
        message=fake_email,
        type=models.EmailMessage.HTML_CONTENT_TYPE
    )
