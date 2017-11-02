import logging

from django.utils import timezone

from r3sourcer.apps.core.utils.companies import get_master_companies_by_contact

from r3sourcer.apps.sms_interface.services import BaseSMSService
from .models import TwilioCredential, TwilioPhoneNumber, TwilioAccount, TwilioSMSMessage

logger = logging.getLogger(__name__)


class TwilioSMSService(BaseSMSService):
    def process_sms_send(self, sms_message):
        twilio_account = TwilioAccount.objects.get(phone_numbers__phone_number=sms_message.from_number)

        sms_message.sid = twilio_account.client.messages.create(body=sms_message.text, from_=sms_message.from_number,
                                                                to=sms_message.to_number).sid
        sms_message.save(update_fields=['sid'])

    def process_sms_fetch(self):
        sms_list = []

        """ Fetch all credentials from db """
        c_items = TwilioCredential.objects.all()

        for c in c_items.iterator():
            """ Update current credential (numbers, accounts, messages) """

            phone_numbers = []
            last_sync = timezone.now()
            for n in c.client.phone_numbers.iter():
                phone_numbers.append(TwilioPhoneNumber.fetch_remote(n, c.company))

            for remote_account in c.client.accounts.iter():
                account = TwilioAccount.fetch_remote(c, remote_account)

                """ Update current account (messages) """
                params = {
                    'date_sent>': account.get_last_sync()}  # get all messages sent_at after `self.get_last_sync()`

                acc_last_sync = timezone.now().date()
                logger.info("Sync params: {}".format(params))

                for sms_message in remote_account.messages.iter(**params):
                    sms_list.append(TwilioSMSMessage.fetch_remote(account, sms_message))

                account.last_sync = acc_last_sync
                account.save(update_fields=['last_sync'])

            acc_sid_list = TwilioPhoneNumber.objects.filter(twilio_accounts=None).values_list('account_sid', flat=True)

            for sid in acc_sid_list:
                if TwilioAccount.objects.filter(sid=sid).exists():
                    TwilioAccount.objects.get(sid=sid).phone_numbers.add(
                        *TwilioPhoneNumber.objects.filter(account_sid=sid)
                    )

            c.last_sync = last_sync
            c.save(update_fields=['last_sync'])

        return sms_list

    @classmethod
    def get_sender_phones(cls, contact):
        companies = get_master_companies_by_contact(contact)
        return TwilioPhoneNumber.objects.filter(company__in=companies)
