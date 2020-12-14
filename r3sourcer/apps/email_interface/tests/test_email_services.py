from datetime import datetime

import freezegun
import mock
import pytest

from django.utils import timezone

from r3sourcer.apps.core.models import Company
from r3sourcer.apps.email_interface.exceptions import EmailBaseServiceError
from r3sourcer.apps.email_interface.models import EmailMessage
from r3sourcer.apps.email_interface.services import BaseEmailService, FakeEmailService, SMTPEmailService
from r3sourcer.apps.email_interface.utils import get_email_service


class EmailTestService(BaseEmailService):

    def process_email_send(self, email_message):
        pass  # pragma: no cover


@pytest.mark.django_db
class TestEmailServices:

    @pytest.fixture
    def service(self):
        return EmailTestService()

    def test_get_default_fake_email_service(self):
        service = get_email_service()

        assert isinstance(service, FakeEmailService)

    def test_get_service_by_name(self):
        service_class_name = '%s.%s' % (EmailTestService.__module__,
                                        EmailTestService.__name__)
        service = get_email_service(service_class_name)

        assert isinstance(service, EmailTestService)

    def test_get_service_by_name_settings_set(self, settings):
        service_class_name = '%s.%s' % (EmailTestService.__module__,
                                        EmailTestService.__name__)
        settings.EMAIL_SERVICE_ENABLED = True
        settings.EMAIL_SERVICE_CLASS = '%s.%s' % (
            FakeEmailService.__module__, FakeEmailService.__name__
        )
        service = get_email_service(service_class_name)

        assert isinstance(service, EmailTestService)

    def test_get_service_from_settings(self, settings):
        service_class_name = '%s.%s' % (EmailTestService.__module__,
                                        EmailTestService.__name__)
        settings.EMAIL_SERVICE_ENABLED = True
        settings.EMAIL_SERVICE_CLASS = service_class_name
        service = get_email_service()

        assert isinstance(service, EmailTestService)

    def test_get_fake_service_settings_email_service_disabled(self, settings):
        service_class_name = '%s.%s' % (EmailTestService.__module__,
                                        EmailTestService.__name__)
        settings.EMAIL_SERVICE_ENABLED = False
        settings.EMAIL_SERVICE_CLASS = service_class_name
        service = get_email_service()

        assert isinstance(service, FakeEmailService)

    @mock.patch('r3sourcer.apps.email_interface.utils.get_email_service',
                return_value=FakeEmailService)
    def test_fake_email_service_send(self, mock_get_service):
        service = FakeEmailService()
        service.send('test@test.com', 'test', 'test text')

        email_message = EmailMessage.objects.all().first()
        assert email_message.message_id.startswith('FAKE')

    @mock.patch.object(EmailTestService, 'process_email_send')
    def test_send_email_text(self, mock_email_send):
        mock_email_send.return_value = None

        service = EmailTestService()
        service.send('test@test.com', 'test', 'test text')

        assert EmailMessage.objects.all().count() == 1
        assert mock_email_send.called

    @mock.patch.object(EmailTestService, 'process_email_send')
    def test_send_email_html(self, mock_email_send):
        mock_email_send.return_value = None

        service = EmailTestService()
        service.send('test@test.com', 'test', 'test text', 'test html')

        assert EmailMessage.objects.all().count() == 1
        assert mock_email_send.called

    @mock.patch.object(EmailTestService, 'process_email_send')
    def test_send_email_text_service_exception(self, mock_email_send):
        mock_email_send.side_effect = EmailBaseServiceError

        service = EmailTestService()
        service.send('test@test.com', 'test', 'test text')

        email_message = EmailMessage.objects.all().first()
        assert email_message.error_message is not None

    def test_send_email_list_recipients(self):
        service = EmailTestService()
        service.send(['test@test.com'], 'test', 'test text')

        assert EmailMessage.objects.all().count() == 1

    def test_send_email_no_recipients(self):
        service = EmailTestService()
        service.send(None, 'test', 'test text')

        assert not EmailMessage.objects.exists()

    def test_send_email_wrong_type_recipients(self):
        service = EmailTestService()
        service.send({}, 'test', 'test text')

        assert not EmailMessage.objects.exists()

    @mock.patch.object(EmailTestService, 'send')
    def test_send_tpl(self, mock_send, service, email_template):
        service.send_tpl('test@test.com', tpl_name='Email Template')

        mock_send.assert_called_with(
            'test@test.com', 'subject', 'template',
            html_message='', from_email=None, template=email_template
        )

    @mock.patch.object(EmailTestService, 'send')
    @mock.patch.object(Company, 'languages')
    def test_send_tpl_slug(self, mock_company, mock_send, service, email_template):
        service.send_tpl('test@test.com', mock_company, tpl_name='email-template')

        mock_send.assert_called_with(
            'test@test.com', 'subject', 'template',
            html_message='', from_email=None, template=email_template
        )

    @mock.patch('r3sourcer.apps.email_interface.services.logger')
    @mock.patch.object(EmailTestService, 'send')
    @mock.patch.object(Company, 'languages')
    def test_send_tpl_not_found(self, mock_company, mock_send, mock_log, service):
        service.send_tpl('test@test.com', mock_company, 'sms')

        assert mock_log.exception.called
        assert not mock_send.called
