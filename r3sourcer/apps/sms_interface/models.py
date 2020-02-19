import datetime
import logging
import re

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import F
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices

from r3sourcer import ref
from r3sourcer.apps.core.models import UUIDModel, Company, Contact, TemplateMessage, TimeZoneUUIDModel
from r3sourcer.apps.sms_interface.managers import SMSMessageObjectOwnerManager
from r3sourcer.apps.sms_interface.mixins import DeadlineCheckingMixin

logger = logging.getLogger(__name__)


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
        on_delete=models.CASCADE,
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


class SMSMessage(DeadlineCheckingMixin, TimeZoneUUIDModel):

    INVALID_RECIPIENT = _("Invalid recipient instance")

    TYPE_CHOICES = Choices(
        ('SENT', _("SMS sent")),
        ('RECEIVED', _("SMS received")),
        ('UNKNOWN', _('SMS Unknown')),
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
        default=TYPE_CHOICES.UNKNOWN,
    )
    reply_to = models.ForeignKey(
        'sms_interface.SMSMessage',
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
    template = models.ForeignKey(
        'sms_interface.SMSTemplate',
        verbose_name=_("Template"),
        null=True,
        blank=True
    )
    company = models.ForeignKey(
        'core.Company',
        null=True,
        blank=True,
        verbose_name=_('Company'),
    )
    segments = models.IntegerField(
        verbose_name=_('Number of segments'),
        default=0
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
    sent_at = ref.DTField(
        verbose_name=_("Sent at"),
        blank=True,
        null=True,
    )  # delivered/sent date

    # for optimization
    check_delivery_at = ref.DTField(
        verbose_name=_("Check delivery date"),
        blank=True,
        null=True,
    )
    check_reply_at = ref.DTField(
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

    objects = SMSMessageObjectOwnerManager()

    @property
    def geo(self):
        return self.__class__.objects.filter(
            pk=self.pk,
            company__company_addresses__hq=True,
        ).annotate(
            longitude=F('company__company_addresses__address__longitude'),
            latitude=F('company__company_addresses__address__latitude')
        ).values_list('longitude', 'latitude').get()

    @property
    def sent_at_tz(self):
        return self.utc2local(self.sent_at)

    @property
    def sent_at_utc(self):
        return self.sent_at

    @property
    def check_delivery_at_tz(self):
        return self.utc2local(self.check_delivery_at)

    @property
    def check_delivery_at_utc(self):
        return self.check_delivery_at

    @property
    def check_reply_at_tz(self):
        return self.utc2local(self.check_reply_at)

    @property
    def check_reply_at_utc(self):
        return self.check_reply_at

    def is_late_reply(self):
        sent_message = self.get_sent_by_reply(check_reply=False)
        return (
            self.type == self.TYPE_CHOICES.RECEIVED and
            not self.get_sent_by_reply() and
            sent_message and
            not SMSMessage.objects.filter(
                sent_at__range=[sent_message.sent_at_utc, self.sent_at_utc],
                from_number=sent_message.from_number,
                to_number=sent_message.to_number
            ).exclude(id__in=[self.pk, sent_message.id]).exists()
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
        if self.reply_timeout:
            reply_timedelta = datetime.timedelta(minutes=self.reply_timeout)
            self.check_reply_at = self.now_utc + reply_timedelta

        if self.delivery_timeout:
            d_timedelta = datetime.timedelta(minutes=self.delivery_timeout)
            self.check_delivery_at = self.now_utc + d_timedelta

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.set_check_dates()
        super().save(*args, **kwargs)

    def get_sent_by_reply(self, check_reply=True):
        try:
            return self.__class__.objects.filter(
                sent_at__lte=self.sent_at_utc,
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
        return [
            SMSRelatedObject.objects.get_or_create(
                object_id=obj.id if isinstance(obj, models.Model) else obj['object_id'],
                sms=self,
                defaults=(
                    {'content_object': obj} if isinstance(obj, models.Model) else {'content_type_id': obj['content_type']}
                )
            ) for obj in args if isinstance(obj, (dict, models.Model))
        ]

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

    @classmethod
    def owned_by_lookups(cls, owner):
        res = [models.Q(company=owner)]

        if isinstance(owner, Company):
            phone_numbers = owner.twilio_credentials.values_list(
                'accounts_list__phone_numbers__phone_number', flat=True
            )
            contact_phone_numbers = Contact.objects.owned_by(owner).values_list('phone_mobile', flat=True)
            res.extend([
                models.Q(from_number__in=phone_numbers), models.Q(to_number__in=phone_numbers),
                models.Q(from_number__in=contact_phone_numbers), models.Q(to_number__in=contact_phone_numbers),
            ])

        return res

    def __str__(self):
        return '{} -> {}'.format(self.from_number, self.to_number)

    def is_delivered(self):
        return self.status in [
            self.STATUS_CHOICES.RECEIVED,
            self.STATUS_CHOICES.DELIVERED
        ]

    class Meta:
        ordering = ['-sent_at']
        verbose_name = _("SMS message")
        verbose_name_plural = _("SMS messages")


class SMSRelatedObject(UUIDModel):
    """
    Related object for SMSMessage.
    """

    sms = models.ForeignKey(
        'sms_interface.SMSMessage',
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


class RelatedSMSMixin:
    """
    Would be used in models with linked sms messages.
    """

    def get_all_related_sms(self):
        return SMSMessage.objects.filter(
            id__in=set(SMSRelatedObject.objects.filter(
                object_id=self.pk,
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

    company = models.ForeignKey(
        'core.Company',
        verbose_name=_("Master company"),
        on_delete=models.CASCADE,
        related_name='sms_templates',
        null=True,
        blank=True,
    )

    subject_template = ''
    message_html_template = ''

    class Meta:
        verbose_name = _("SMS Template")
        verbose_name_plural = _("SMS Templates")
        ordering = ['name']


class DefaultSMSTemplate(models.Model):
    name = models.CharField(
        max_length=256,
        default="",
        verbose_name=_("Name"),
        db_index=True
    )
    slug = models.SlugField()
    message_text_template = models.TextField(
        default="",
        verbose_name=_("Text template"),
    )

    reply_timeout = models.IntegerField(
        default=10,
        verbose_name=_("Reply timeout"),
        help_text=_("Minutes")
    )

    delivery_timeout = models.IntegerField(
        default=10,
        verbose_name=_("Delivery timeout"),
        help_text=_("Minutes")
    )

    class Meta:
        verbose_name = _("Default SMS Template")
        verbose_name_plural = _("Default SMS Templates")
        ordering = ['name']
