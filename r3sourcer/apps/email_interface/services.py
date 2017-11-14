import logging
import smtplib
from abc import ABCMeta, abstractmethod

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from r3sourcer.apps.email_interface import models as email_models
from r3sourcer.apps.email_interface.exceptions import RecipientsInvalidInstance, EmailBaseServiceError


logger = logging.getLogger(__name__)


class BaseEmailService(metaclass=ABCMeta):

    @transaction.atomic
    def send(self, recipients, subject, text_message, html_message=None,
             from_email=None, template=None, **kwargs):

        try:
            if not from_email:
                from_email = settings.NO_REPLY_EMAIL

            email_message = None
            if isinstance(recipients, str):
                to_addresses = recipients
            elif isinstance(recipients, (tuple, list)):
                to_addresses = ",".join(recipients)
            else:
                raise RecipientsInvalidInstance('Recipients should be either string or list')

            now_dt = timezone.now()

            email_message = email_models.EmailMessage(
                state=email_models.EmailMessage.STATE_CHOICES.CREATED,
                sent_at=None,
                from_email=from_email,
                subject=subject,
                created_at=now_dt,
                to_addresses=to_addresses,
                template=template
            )
            email_message.save()

            if text_message:
                email_models.EmailBody.objects.create(
                    content=text_message, type=email_models.EmailMessage.TEXT_CONTENT_TYPE, message=email_message
                )

            if html_message:
                email_models.EmailBody.objects.create(
                    content=html_message, type=email_models.EmailMessage.HTML_CONTENT_TYPE, message=email_message
                )

            self.process_email_send(email_message)

            logger.info("E-mail message sent: sid={}; recipients={}".format(
                email_message.message_id, email_message.to_addresses
            ))
        except EmailBaseServiceError as e:
            if email_message:
                email_message.error_message = str(e)
                email_message.save()

    @transaction.atomic
    def send_tpl(self, recipients, from_email=None, tpl_name=None, **kwargs):
        try:
            template = email_models.EmailTemplate.objects.get(
                Q(name=tpl_name) | Q(slug=tpl_name)
            )
            compiled = template.compile(**kwargs)
            message = compiled['text']
            subject = compiled['subject']
        except email_models.EmailTemplate.DoesNotExist:
            logger.exception('Cannot find email template with name %s', tpl_name)
        else:
            self.send(recipients, subject, message, from_email=from_email, template=template, **kwargs)

    @abstractmethod
    def process_email_send(self, email_message):
        """
        Actually send e-mail message

        should throws EmailBaseServiceError or its subclasses if error occurred
        """
        pass  # pragma: no cover


class FakeEmailService(BaseEmailService):

    def process_email_send(self, email_message):
        email_message.message_id = 'FAKE_%s' % email_message.id
        email_message.save(update_fields=['message_id'])


class SMTPEmailService(BaseEmailService):

    def process_email_send(self, email_message):
        email_message.message_id = email_message.id
        email_message.state = email_models.EmailMessage.STATE_CHOICES.SENDING
        email_message.save(update_fields=['state', 'message_id'])

        is_no_reply_email = email_message.from_email == settings.DEFAULT_SMTP_EMAIL

        # conf message
        msg = MIMEMultipart('related')
        msg['From'] = email_message.from_email
        msg['To'] = email_message.to_addresses
        msg['Subject'] = email_message.subject
        if not is_no_reply_email:
            msg.add_header('Reply-To', email_message.from_email)

        msg_alternative = MIMEMultipart('alternative')
        msg.attach(msg_alternative)

        if email_message.has_text_message():
            msg_alternative.attach(MIMEText(email_message.get_text_body(), 'plain'))

        if email_message.has_html_message():
            msg_alternative.attach(MIMEText(email_message.get_html_body(), 'html'))

        smtp_server_args = {
            'host': settings.DEFAULT_SMTP_SERVER,
            'port': settings.DEFAULT_SMTP_PORT,
        }
        smpt_auth_args = {
            'user': settings.DEFAULT_SMTP_EMAIL,
            'password': settings.DEFAULT_SMTP_PASSWORD,
        }

        try:
            smtp_conn = smtplib.SMTP(**smtp_server_args)
            smtp_conn.ehlo()

            if settings.DEFAULT_SMTP_TLS:
                smtp_conn.starttls()
                smtp_conn.ehlo()

            smtp_conn.login(**smpt_auth_args)
            smtp_conn.sendmail(email_message.from_email, email_message.to_addresses.split(','), msg.as_string())
            smtp_conn.close()

            email_message.state = email_models.EmailMessage.STATE_CHOICES.SENT
            email_message.save(update_fields=['state'])
        except Exception:
            logger.exception('Cannot send email using SMTP')

            email_message.state = email_models.EmailMessage.STATE_CHOICES.ERROR
            email_message.save(update_fields=['state'])
