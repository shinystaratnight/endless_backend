import datetime
import logging
import pytz
import re

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_save
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices

from r3sourcer.apps.core.models import UUIDModel, Company, Contact, TemplateMessage
from r3sourcer.apps.sms_interface.mixins import DeadlineCheckingMixin


logger = logging.getLogger(__name__)


def replace_timezone(dt, time_zone=pytz.utc):
    if isinstance(dt, timezone.datetime):
        return dt.replace(tzinfo=time_zone)
    return dt


def disable_default_flag_for_phones(**kwargs):
    """
    Disable is_default value for all phone numbers if instance 

    :param kwargs: 
    :return: 
    """
    if kwargs['instance'].is_default:
        kwargs['instance'].company.phone_numbers.exclude(id=kwargs['instance'].id).update(is_default=False)


class PhoneNumber(UUIDModel):

    sid = models.CharField(
        max_length=254,
        verbose_name=_("SID"),
        unique=True,
        editable=False,
        help_text=_("Number ID"),
    )
    phone_number = models.CharField(
        max_length=32,
        verbose_name=_("Phone"),
    )
    friendly_name = models.CharField(
        max_length=512,
        default="",
        editable=False,
        verbose_name=_("Friendly name"),
    )
    company = models.ForeignKey(
        Company,
        verbose_name=_("Company"),
        related_name='phone_numbers'
    )

    # capabilities
    sms_enabled = models.BooleanField(
        default=True,
        verbose_name=_("SMS enabled"),
    )
    mms_enabled = models.BooleanField(
        default=True,
        verbose_name=_("MMS enabled"),
    )
    voice_enabled = models.BooleanField(
        default=True,
        verbose_name=_("VOICE enabled"),
    )

    is_default = models.BooleanField(
        verbose_name=_("Using as default for company"),
        default=False
    )

    def __str__(self):
        return self.phone_number

    class Meta:
        verbose_name = _("Phone number")
        verbose_name_plural = _("Phone numbers")


post_save.connect(disable_default_flag_for_phones, sender=PhoneNumber)


class FakeSMSManager(models.Manager):

    def get_queryset(self, *args, **kwargs):
        return super(FakeSMSManager, self).get_queryset(
            *args, **kwargs
        ).filter(is_fake=True)


class SMSMessage(DeadlineCheckingMixin, UUIDModel):

    INVALID_RECIPIENT = _("Invalid recipient instance")

    TYPE_CHOICES = Choices(
        ('SENT', _("SMS sent")),
        ('RECEIVED', _("SMS received")),
    )

    STATUS_CHOICES = Choices(
        ('ACCEPTED', _("Accepted")),
        ('SENT', _("Sent")),
        ('QUEUED', _("Queued")),
        ('SENDING', _("Sending")),
        ('SENT', _("Sent")),
        ('FAILED', _("Failed")),
        ('DELIVERED', _("Delivered")),
        ('UNDELIVERED', _("Undelivered")),
        ('RECEIVED', _("Received")),
    )

    # main data
    sid = models.CharField(
        max_length=254,
        verbose_name=_("SID"),
        editable=False,
        help_text=("Twillio Message ID"),
    )
    status = models.CharField(
        max_length=25,
        verbose_name=_("Status"),
        null=True,
        blank=True,
        choices=STATUS_CHOICES,
    )
    type = models.CharField(
        max_length=15,
        blank=True,
        verbose_name=_("Type"),
        choices=TYPE_CHOICES,
        default=TYPE_CHOICES.SENT,
    )
    reply_to = models.ForeignKey(
        'self',
        verbose_name=_("Reply to"),
        related_name='replyto',
        blank=True,
        null=True,
        on_delete=models.PROTECT,
    )
    text = models.TextField(
        verbose_name=_("Text message"),
        null=True,
        blank=True,
    )
    trash = models.BooleanField(
        verbose_name=_("Trash"),
        default=False,
    )
    related_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    related_object_id = models.UUIDField(
        null=True,
        blank=True,
    )
    related_object = GenericForeignKey(
        'related_content_type',
        'related_object_id'
    )

    # check message status
    check_delivered = models.BooleanField(
        verbose_name=_("Check delivered status after timeout"),
        default=False,
    )
    check_reply = models.BooleanField(
        verbose_name=_("Check reply status after timeout"),
        default=False,
    )

    # phones
    from_number = models.CharField(
        max_length=25,
        verbose_name=_("From number"),
        null=True,
        blank=True,
        default='',
    )
    to_number = models.CharField(
        max_length=25,
        verbose_name=_("To number"),
        null=True,
        blank=True,
    )

    # dates
    sent_at = models.DateTimeField(
        verbose_name=_("Sent at"),
        blank=True,
        null=True,
    )  # delivered/sent date

    # for optimization
    check_delivery_at = models.DateTimeField(
        verbose_name=_("Check delivery date"),
        blank=True,
        null=True,
    )
    check_reply_at = models.DateTimeField(
        verbose_name=_("Check reply at"),
        blank=True,
        null=True,
    )
    is_fetched = models.BooleanField(
        _("SMS fetched"),
        default=False,
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

    # late reply
    late_reply = models.ForeignKey(
        'self',
        verbose_name=_("Late reply"),
        related_name='sent_sms_messages',
        default=None,
        null=True,
        blank=True,
    )

    # tests
    is_fake = models.BooleanField(
        _("Fake sms"),
        default=False,
    )

    def is_late_reply(self):
        sent_message = self.get_sent_by_reply(check_reply=False)
        return (
            self.type == self.TYPE_CHOICES.RECEIVED and
            not self.get_sent_by_reply() and
            sent_message and
            not SMSMessage.objects.filter(
                sent_at__range=[sent_message.sent_at, self.sent_at],
                from_number=sent_message.from_number,
                to_number=sent_message.to_number
            ).exclude(id__in=[self.id, sent_message.id]).exists()
        )

    def is_positive_answer(self):
        pattern = r'^(y[a-z]s|y|ye[a-z]{0,1}?|yse|yeah|ya(s*)|yo|ok)(\W(.|\n)*)?$'
        return bool(re.match(pattern, (self.text or "").strip(), re.I))

    def is_negative_answer(self):
        pattern = r'^(n|no|nah|nop|nope|not|sorry|nay)(\W(.|\n)*)?$'
        return bool(re.match(pattern, (self.text or "").strip(), re.I))

    def is_answer(self):
        return self.is_positive_answer() or self.is_negative_answer()

    def is_stop_message(self):
        return bool(re.match('^(stop|stopall|cancel|end|quit)$', (self.text or "").strip(), re.I))

    def is_start_message(self):
        return bool(re.match('^(start|unstop|yes)$', (self.text or "").strip(), re.I))

    def is_login(self):
        return bool(re.match('^(log|log ?in|sign ?in)$', (self.text or "").strip(), re.I))

    def set_check_dates(self):
        # bind current date + timedelta (timeout)
        if self.reply_timeout:
            reply_timedelta = datetime.timedelta(minutes=self.reply_timeout)
            self.check_reply_at = timezone.now() + reply_timedelta
        if self.delivery_timeout:
            d_timedelta = datetime.timedelta(minutes=self.delivery_timeout)
            self.check_delivery_at = timezone.now() + d_timedelta

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.set_check_dates()
        super(SMSMessage, self).save(*args, **kwargs)

    def get_sent_by_reply(self, check_reply=True):
        try:
            return self.__class__.objects.filter(
                sent_at__lte=self.sent_at,
                from_number=self.to_number,
                to_number=self.from_number,
                type=self.TYPE_CHOICES.SENT,
                check_reply=check_reply
            ).latest('sent_at')
        except self.__class__.DoesNotExist:
            return None

    def has_contact_relation(self):
        return Contact.objects.filter(
            phone_mobile__in=[self.from_number, self.to_number]
        ).exists()

    def add_related_objects(self, *args):
        logger.info("Add related objects to message {}({}): {}".format(self.id, self, args))
        return [SMSRelatedObject.objects.get_or_create(
            object_id=obj.id, sms=self,
            defaults={'content_object': obj}
        ) for obj in args if isinstance(obj, models.Model)]

    def get_related_objects(self, obj_type=None):
        qry = models.Q()
        if obj_type is not None:
            qry = models.Q(content_type=obj_type)

        return [
            obj.content_object
            for obj in self.related_objects.filter(qry) if obj.content_object
        ]

    def no_check_reply(self):
        self.check_reply = False
        self.save(update_fields=['check_reply'])
        logger.info("Message {} ({}) will not check reply".format(self.id, self))

    def __str__(self):
        return '{} -> {}'.format(self.from_number, self.to_number)

    class Meta:
        ordering = ['-sent_at']
        verbose_name = _("SMS message")
        verbose_name_plural = _("SMS messages")


class SMSRelatedObject(UUIDModel):
    """
    Related object for SMSMessage.
    """

    sms = models.ForeignKey(
        SMSMessage,
        verbose_name=_("SMS message"),
        related_name='related_objects'
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE
    )
    object_id = models.UUIDField()
    content_object = GenericForeignKey()

    def __str__(self):
        return '{}: {}'.format(self.content_type.name, self.content_object)

    class Meta:
        verbose_name = _("SMS related object")
        verbose_name_plural = _("SMS related objects")


class RelatedSMSMixin(object):
    """
    Would be used in models with linked sms messages.
    """

    def get_all_related_sms(self):
        return SMSMessage.objects.filter(
            id__in=set(SMSRelatedObject.objects.filter(
                object_id=self.id
            ).values_list('sms', flat=True))
        ).order_by('sent_at')


class SMSTemplate(TemplateMessage):
    SMS = 'sms'
    TYPE_CHOICES = (
        (SMS, _("SMS")),
    )

    type = models.CharField(
        max_length=8,
        choices=TYPE_CHOICES,
        verbose_name=_("Type")
    )

    subject_template = ''
    message_html_template = ''

    class Meta:
        verbose_name = _("SMS Template")
        verbose_name_plural = _("SMS Templates")
        ordering = ['name']
