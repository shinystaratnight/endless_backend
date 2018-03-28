import logging

from django.contrib.sites.shortcuts import get_current_site
from django.utils import timezone

from r3sourcer.apps.core.models import SiteCompany, Company
from r3sourcer.apps.core.utils.companies import get_master_companies_by_contact
from r3sourcer.apps.sms_interface.services import BaseSMSService
from r3sourcer.apps.twilio import models

logger = logging.getLogger(__name__)


class TwilioSMSService(BaseSMSService):
    def process_sms_send(self, sms_message):
        try:
            twilio_account = models.TwilioAccount.objects.get(phone_numbers__phone_number=sms_message.from_number)
        except models.TwilioAccount.DoesNotExist:
            current_site = get_current_site(None)
            master_type = Company.COMPANY_TYPES.master
            site_companies = SiteCompany.objects.filter(
                site=current_site, company__type=master_type,
            ).values_list('company_id', flat=True)

            twilio_account = models.TwilioAccount.objects.filter(credential__company__in=site_companies).last()

            if not twilio_account:
                logger.warn('Cannot find Twilio number')
                return

        sms_message.sid = twilio_account.client.api.account.messages.create(
            body=sms_message.text, from_=sms_message.from_number, to=sms_message.to_number
        ).sid
        sms_message.save(update_fields=['sid'])

    def process_sms_fetch(self):
        sms_list = []

        """ Fetch all credentials from db """
        c_items = models.TwilioCredential.objects.all()

        for c in c_items.iterator():
            """ Update current credential (numbers, accounts, messages) """

            phone_numbers = []
            last_sync = timezone.now()
            for n in c.client.api.incoming_phone_numbers.stream():
                phone_numbers.append(models.TwilioPhoneNumber.fetch_remote(n, c.company))

            for remote_account in c.client.api.accounts.stream():
                account = models.TwilioAccount.fetch_remote(c, remote_account)

                """ Update current account (messages) """
                params = {
                    'date_sent_after': account.get_last_sync()
                }  # get all messages sent_at after `self.get_last_sync()`

                acc_last_sync = timezone.localtime(timezone.now()).date()
                logger.info("Sync params: {}".format(params))

                for sms_message in remote_account.messages.stream(**params):
                    sms_list.append(models.TwilioSMSMessage.fetch_remote(account, sms_message))

                account.last_sync = acc_last_sync
                account.save(update_fields=['last_sync'])

            acc_sid_list = models.TwilioPhoneNumber.objects.filter(twilio_accounts=None).values_list(
                'account_sid', flat=True
            )

            for sid in acc_sid_list:
                if models.TwilioAccount.objects.filter(sid=sid).exists():
                    models.TwilioAccount.objects.get(sid=sid).phone_numbers.add(
                        *models.TwilioPhoneNumber.objects.filter(account_sid=sid)
                    )

            c.last_sync = last_sync
            c.save(update_fields=['last_sync'])

        return sms_list

    @classmethod
    def get_sender_phones(cls, contact):
        companies = get_master_companies_by_contact(contact)
        return models.TwilioPhoneNumber.objects.filter(company__in=companies)
