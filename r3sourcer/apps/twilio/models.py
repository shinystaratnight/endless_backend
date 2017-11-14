from django.core.exceptions import ValidationError
from django.db import transaction
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from r3sourcer.apps.sms_interface.mixins import DeadlineCheckingMixin
from r3sourcer.apps.sms_interface.models import PhoneNumber, SMSMessage, replace_timezone
from model_utils import Choices
from twilio import TwilioRestException
from twilio.rest import TwilioRestClient

import datetime
import logging

from r3sourcer.apps.core.models import UUIDModel

logger = logging.getLogger(__name__)


def get_parse_date_from():
    return timezone.now() - datetime.timedelta(hours=24)


class TwilioCredential(UUIDModel, DeadlineCheckingMixin):

    INVALID_CREDENTIALS = _("Invalid account sid/auth token: %s")

    company = models.ForeignKey(
        'core.Company',
        verbose_name=_("Company"),
        related_name='twilio_credentials'
    )

    sid = models.CharField(
        verbose_name=_("Twilio account id"),
        max_length=256
    )

    auth_token = models.CharField(
        verbose_name=_("Twilio auth token"),
        max_length=256
    )

    last_sync = models.DateTimeField(
        verbose_name=_("Last sync"),
        default=None,
        null=True
    )

    parse_from_date = models.DateField(
        verbose_name=_("Parse from date"),
        default=get_parse_date_from
    )

    class Meta:
        verbose_name = _("Twilio credentials")
        verbose_name_plural = _("Twilio credentials")

    def __str__(self):
        return str(self.company)

    def check_connection(self):
        """ Check account credentials """
        try:
            self.client.accounts.list()
        except Exception as e:
            error_text = self.INVALID_CREDENTIALS % str(e)
            raise ValidationError({'sid': error_text, 'auth_token': error_text})

    def clean(self):
        self.check_connection()

    @cached_property
    def client(self):
        return TwilioRestClient(self.sid, self.auth_token)

    @property
    def is_synced(self):
        return bool(self.last_sync)


class TwilioPhoneNumber(PhoneNumber):

    account_sid = models.CharField(
        verbose_name=_("Account SID"),
        max_length=128,
        editable=False
    )

    @classmethod
    def fetch_remote(cls, remote_phone, company):
        values_phone = {
            'sid': remote_phone.sid,
            'company': company,
            'account_sid': remote_phone.account_sid,
            'created_at': replace_timezone(remote_phone.date_created),
            'updated_at': replace_timezone(remote_phone.date_updated),
            'friendly_name': remote_phone.friendly_name,
            'phone_number': remote_phone.phone_number,
            'sms_enabled': remote_phone.capabilities['sms'],
            'mms_enabled': remote_phone.capabilities['mms'],
            'voice_enabled': remote_phone.capabilities['voice']
        }

        phone, created = cls.objects.update_or_create(sid=remote_phone.sid, defaults=values_phone)
        return phone

    class Meta:
        verbose_name = _("Twilio phone number")
        verbose_name_plural = _("Twilio phone numbers")


class TwilioAccount(UUIDModel):
    """ Twilio account """

    STATUS_CHOICES = Choices(
        ('ACTIVE', _("Active")),
        ('CLOSED', _("Closed")),
        ('SUSPENDED', _("Suspended"))
    )
    STATUS_VALUES = {True: _("Enabled"), True: _("Disabled")}
    INCORRECT_STATUS_ERROR = _("Incorrect status value. Available choices: %s")
    TIMEDELTA_DAYS_FETCH = 24

    phone_numbers = models.ManyToManyField(
        TwilioPhoneNumber,
        verbose_name=_("Phone numbers"),
        related_name="twilio_accounts"
    )

    # base twilio credentials info
    credential = models.ForeignKey(
        TwilioCredential,
        verbose_name=_("Credentials"),
        related_name='accounts_list',
        on_delete=models.PROTECT
    )

    sid = models.CharField(
        verbose_name=_("SID"),
        max_length=256,
        help_text=_("Twilio account SID"),
        unique=True,
        editable=False
    )

    # parent data
    owner_account_sid = models.CharField(
        verbose_name=_("Owner account SID"),
        max_length=256,
        default="",
        blank=True
    )

    # main sync data
    account_type = models.CharField(
        verbose_name=_("Type"),
        max_length=16,
        default='Full',
        editable=False
    )

    status = models.CharField(
        verbose_name=_("Status"),
        default=STATUS_CHOICES.ACTIVE,
        choices=STATUS_CHOICES,
        max_length=16
    )

    friendly_name = models.CharField(
        verbose_name=_("Friendly name"),
        max_length=512,
        default="",
        editable=False
    )

    # last sync date
    last_sync = models.DateField(
        verbose_name=_("Last sync account"),
        default=None,
        null=True,
        editable=False
    )

    def __str__(self):
        return '#ID:{}: #{}'.format(self.sid, self.credential)

    @cached_property
    def client(self):
        return self.credential.client

    @property
    def remote_record(self):
        return self.client.accounts.get(self.sid)

    def get_owner_account(self):
        """
        :return: TwilioAccount or None
        """
        return TwilioAccount.objects.filter(owner_account_sid=self.owner_account_sid).first()

    def is_owner_for_number(self, phone_number):
        return self.phone_numbers.filter(phone_number=phone_number).exists()

    def update_status(self, status):
        """
        Update remote status

        :param status: string of STATUS_CHOICES
        """
        values_set = self.STATUS_CHOICES._db_values
        assert status.upper() in values_set, self.INCORRECT_STATUS_ERROR % list(values_set)
        self.remote_record.update_instance(status=status.lower())
        old_status = self.status
        self.status = status
        self.save(update_fields=['status'])
        logger.error("Error update status account: {}  {}=>{}".format(self.sid, old_status, status))

    def get_message(self, message_sid):
        try:
            return self.client.messages.get(message_sid)
        except TwilioRestException as e:
            logger.error("[Get message error]: {}".format(e))

    def get_last_sync(self):
        last_sync = self.last_sync
        if last_sync:
            last_sync -= datetime.timedelta(hours=self.TIMEDELTA_DAYS_FETCH)  # last_sync - TIMEDELTA_DAYS
        else:
            last_sync = self.credential.parse_from_date
        return last_sync

    @classmethod
    def fetch_remote(cls, credential, remote_account):
        values_account = {
            'sid': remote_account.sid,
            'credential': credential,
            'status': remote_account.status.upper(),
            'account_type': remote_account.type,
            'friendly_name': remote_account.friendly_name,
            'owner_account_sid': remote_account.owner_account_sid,
        }

        account, created = cls.objects.update_or_create(sid=remote_account.sid, defaults=values_account)

        return account


class TwilioSMSMessage(SMSMessage):

    @classmethod
    @transaction.atomic
    def fetch_remote(cls, account, remote_message):

        # get message type (sent or delivered)
        if remote_message.status == cls.TYPE_CHOICES.RECEIVED.lower():
            message_type = cls.TYPE_CHOICES.RECEIVED
        else:
            message_type = cls.TYPE_CHOICES.SENT

        values_message = {
            'sid': remote_message.sid,
            'from_number': remote_message.from_,
            'to_number': remote_message.to,
            'text': remote_message.body,
            'sent_at': replace_timezone(remote_message.date_sent),
            'updated_at': replace_timezone(remote_message.date_updated),
            'created_at': replace_timezone(remote_message.date_created),
            'status': remote_message.status.upper(),
            'type': message_type,
            'error_code': remote_message.error_code,
            'error_message': remote_message.error_message,
        }

        sms_message, created = cls.objects.select_for_update().update_or_create(sid=remote_message.sid,
                                                                                defaults=values_message)
        return sms_message

    class Meta:
        proxy = True