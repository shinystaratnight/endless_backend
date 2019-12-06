from django.db import models
from django.utils.translation import ugettext_lazy as _
from filer.models import File

from model_utils import Choices

from r3sourcer.apps.core import models as core_models


TEXT_CONTENT_TYPE = 'text/plain'
HTML_CONTENT_TYPE = 'text/html'
PDF_CONTENT_TYPE = 'application/pdf'

FILE_MIME_MAPPING = {
    '.pdf': PDF_CONTENT_TYPE,
}


class EmailTemplate(core_models.TemplateMessage):
    EMAIL = 'email'
    TYPE_CHOICES = (
        (EMAIL, _("Email")),
    )

    type = models.CharField(
        max_length=8,
        choices=TYPE_CHOICES,
        verbose_name=_("Type")
    )

    class Meta:
        verbose_name = _("E-mail Template")
        verbose_name_plural = _("E-mail Templates")
        ordering = ['name']


class EmailMessage(core_models.UUIDModel, models.Model):

    STATE_CHOICES = Choices(
        ('CREATED', _("Created")),
        ('WAIT', _("Waiting")),
        ('SENDING', _("Sending")),
        ('SENT', _("Sent")),
        ('ERROR', _("Error"))
    )

    state = models.CharField(
        default=STATE_CHOICES.CREATED,
        choices=STATE_CHOICES,
        max_length=16,
        verbose_name=_("State sending")
    )

    message_id = models.CharField(
        max_length=256,
        verbose_name=_("Email message id")
    )

    received_at = models.DateTimeField(
        verbose_name=_("When mail received"),
        null=True,
        blank=True
    )

    sent_at = models.DateTimeField(
        verbose_name=_("When mail received"),
        null=True,
        blank=True
    )

    sender_email = models.CharField(
        max_length=512,
        default="",
        verbose_name=_("Sender email")
    )

    from_email = models.CharField(
        max_length=512,
        default="",
        verbose_name=_("From email")
    )

    subject = models.TextField(
        verbose_name=_("Mail subject")
    )

    headers = models.TextField(
        default="",
        verbose_name=_("Headers")
    )

    to_addresses = models.CharField(
        max_length=1024,
        default="",
        blank=True,
        verbose_name=_("Recipients")
    )

    is_read = models.BooleanField(
        default=False,
        verbose_name=_("Seen")
    )

    is_answered = models.BooleanField(
        default=False,
        verbose_name=_("Answered")
    )

    is_draft = models.BooleanField(
        default=True,
        verbose_name=_("Draft")
    )

    deleted = models.BooleanField(
        default=False,
        verbose_name=_("Deleted")
    )

    template = models.ForeignKey(
        EmailTemplate,
        verbose_name=_("Template"),
        default=None,
        null=True,
        blank=True
    )

    # error info
    error_code = models.TextField(
        verbose_name=_("Error code"),
        default="",
        null=True,
        blank=True,
    )
    error_message = models.TextField(
        verbose_name=_("Error message"),
        default="",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("E-mail message")
        verbose_name_plural = _("E-mail messages")

    def __str__(self):
        return 'To {} from {}'.format(self.to_addresses.split(',')[0], self.from_email)

    def has_text_message(self):
        """ Check exists palin TEXT body """
        return self.bodies.filter(type=TEXT_CONTENT_TYPE).exists()

    def has_html_message(self):
        """ Check exists HTML body """
        return self.bodies.filter(type=HTML_CONTENT_TYPE).exists()

    def get_text_body(self):
        """ Return TEXT-body or None """
        try:
            return self.bodies.get(type=TEXT_CONTENT_TYPE).content
        except EmailBody.DoesNotExist:
            return None

    def get_html_body(self):
        """ Return HTML-body or None """
        try:
            return self.bodies.get(type=HTML_CONTENT_TYPE).content
        except EmailBody.DoesNotExist:
            return None


class EmailBody(core_models.UUIDModel, models.Model):
    """ Mail message body """

    UUID_PATTERN = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

    content_id = models.IntegerField(
        default=None,
        null=True,
        verbose_name=_("Content id")
    )

    section = models.CharField(
        default="1",
        max_length=8,
        verbose_name=_("Section")
    )

    content = models.TextField(
        verbose_name=_("Mail message body"),
        blank=True,
        null=True
    )

    encoding = models.CharField(
        max_length=32,
        default="",
        verbose_name=_("Encoding")
    )

    mime = models.TextField(
        default="",
        verbose_name=_("Mime")
    )

    message_mime = models.TextField(
        default="",
        verbose_name=_("Message mime")
    )

    size = models.IntegerField(
        default=0,
        verbose_name=_("Size")
    )

    type = models.CharField(
        max_length=32,
        default=TEXT_CONTENT_TYPE,
        verbose_name=_("Type")
    )

    message = models.ForeignKey(
        EmailMessage,
        related_name='bodies',
        verbose_name=_("Email message"),
        on_delete=models.PROTECT
    )

    file = models.ForeignKey(
        File,
        related_name='bodies',
        verbose_name=_('File'),
        on_delete=models.CASCADE,
        null=True
    )

    class Meta:
        verbose_name = _("Body of E-mail message")
        verbose_name_plural = _("Bodies of E-mail messages")

    def __str__(self):
        return 'Message: {}'.format(self.message.message_id)
