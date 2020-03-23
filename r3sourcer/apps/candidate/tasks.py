from datetime import datetime

from django.conf import settings
from django.db import transaction
from django.utils import module_loading

import requests
import stripe

from celery import shared_task
from celery.utils.log import get_task_logger

from r3sourcer.apps.billing import models as billing_models
from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.core.utils import companies as core_companies_utils
from r3sourcer.apps.candidate import models as candidate_models
from r3sourcer.apps.sms_interface.models import SMSTemplate


logger = get_task_logger(__name__)


@shared_task(bind=True)
def send_verify_sms(self, candidate_contact_id, workflow_object_id=None):
    try:
        sms_interface = module_loading.import_string(settings.SMS_SERVICE_CLASS)()
    except ImportError:
        logger.exception('Cannot load SMS service')
        return

    sms_tpl = 'mobile-phone-verification'

    try:
        candidate = candidate_models.CandidateContact.objects.get(id=candidate_contact_id)
    except candidate_models.CandidateContact.DoesNotExist as e:
        logger.exception(e)
        candidate = None

    if candidate is not None:
        with transaction.atomic():
            data_dict = dict(
                contact=candidate.contact,
                manager=candidate.recruitment_agent or candidate.get_closest_company().primary_contact,
                related_obj=candidate,
            )

            if workflow_object_id is not None:
                workflow_object = core_models.WorkflowObject.objects.get(id=workflow_object_id)
                data_dict['related_objs'] = [workflow_object]

            logger.info('Sending phone verify SMS to %s.', candidate.contact)

            master_company = core_companies_utils.get_site_master_company(user=candidate.contact.user)
            sms_template = SMSTemplate.objects.get(company=master_company, slug=sms_tpl)

            sms_interface.send_tpl(to_number=candidate.contact.phone_mobile,
                                   tpl_id=sms_template.id,
                                   **data_dict)


@shared_task()
def buy_candidate(candidate_rel_id, user=None):
    from r3sourcer.apps.logger.main import endless_logger
    try:
        candidate_rel = candidate_models.CandidateRel.objects.get(pk=candidate_rel_id)
        candidate_contact = candidate_rel.candidate_contact
        company = candidate_rel.master_company
        # for country taxes
        tax_percent = 10.0
        if company.get_hq_address():
            country_code = company.get_hq_address().address.country.code2
            try:
                stripe_account = StripeCountryAccount.objects.get(country=country_code)
            except StripeCountryAccount.DoesNotExist:
                stripe_account = StripeCountryAccount.objects.get(country="AU")
            stripe.api_key = stripe_account.stripe_secret_key
            vat_object = core_models.VAT.objects.filter(country=country_code)
            if vat_object:
                tax_percent = vat_object.first().stripe_rate
    except core_models.Company.DoesNotExist as e:
        logger.exception(e)

    try:
        amount = int(candidate_contact.profile_price * 100)
        stripe.InvoiceItem.create(
            customer=company.stripe_customer,
            amount=round(amount / 1.1),
            currency=company.currency,
            description='%s candidate profile purchase for %s' % (str(candidate_contact), company.name)
        )
        invoice = stripe.Invoice.create(customer=company.stripe_customer, tax_percent=tax_percent)
        invoice.pay()
        billing_models.Payment.objects.create(
            company=company,
            type=billing_models.Payment.PAYMENT_TYPES.candidate,
            amount=int(float(candidate_contact.profile_price)),
            stripe_id=invoice['id'],
            invoice_url=invoice['invoice_pdf'],
            status=invoice['status']
        )

        candidate_rel.active = True
        candidate_rel.save()
        candidate_contact.recruitment_agent = candidate_rel.company_contact
        candidate_contact.save(update_fields=['recruitment_agent'])
        for skill in candidate_contact.candidate_skills.all():
            endless_logger.log_instance_change(instance=skill, old_instance=skill, transaction_type='update', user=user)
            endless_logger.log_instance_change(instance=skill, transaction_type='create', user=user)
    except stripe.StripeError as e:
        logger.exception(e)


@shared_task()
def update_superannuation_fund_list():
    file_url = 'http://superfundlookup.gov.au/Tools/DownloadUsiList?download=usi'
    response = requests.get(file_url, stream=True)

    if response.encoding is None:
        response.encoding = 'utf-8'

    lines = response.iter_lines(decode_unicode=True)

    # skip header and delimiter lines
    next(lines)
    next(lines)

    batch = []
    for line in lines:
        if not line:
            continue

        abn = line[0:12].strip()
        product_name = line[234:435].strip()
        usi = line[213:234].strip()

        try:
            defaults = {
                'abn': abn,
                'product_name': product_name,
                'fund_name': line[12:213].strip(),
                'usi': usi,
                'contribution_restrictions': line[435:460].strip().lower() == 'y',
                'from_date': datetime.strptime(line[460:471].strip(), '%Y-%m-%d').date(),
                'to_date': datetime.strptime(line[471:].strip(), '%Y-%m-%d').date(),
            }
        except ValueError:
            continue

        superfund_exist = candidate_models.SuperannuationFund.objects.filter(
            abn=abn, product_name=product_name, usi=usi
        ).first()

        if superfund_exist is None:
            if len(batch) < 50:
                batch.append(candidate_models.SuperannuationFund(**defaults))
            else:
                candidate_models.SuperannuationFund.objects.bulk_create(batch)
                batch = []
        else:
            for key, value in defaults.items():
                setattr(superfund_exist, key, value)
            superfund_exist.save()

    if len(batch) > 0:
        candidate_models.SuperannuationFund.objects.bulk_create(batch)
