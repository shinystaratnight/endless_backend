import logging

from r3sourcer.apps.pricing.models import PriceListRate
from r3sourcer.apps.myob.mappers import InvoiceMapper, ActivityMapper
from r3sourcer.apps.myob.services.base import BaseSync


log = logging.getLogger(__name__)


class InvoiceSync(BaseSync):
    app = "core"
    model = "Invoice"
    mapper_class = InvoiceMapper

    def _get_resource(self):
        return self.client.api.Sale.Invoice.TimeBilling

    def _get_tax_codes(self):
        gst_code = self._get_object_by_field('GST', self.client.api.GeneralLedger.TaxCode, 'Code', True)
        gnr_code = self._get_object_by_field('GNR', self.client.api.GeneralLedger.TaxCode, 'Code', True)
        return {"GST": gst_code['UID'], "GNR": gnr_code['UID']}

    def _find_old_myob_card(self, invoice, resource=None):
        return self._get_object_by_field(
            invoice.myob_number.lower(),
            resource=resource,
        )

    def _create_or_update_activities(self, invoice, tax_codes):
        activities = dict()

        for invoice_line in invoice.invoice_lines.all():
            activity_mapper = ActivityMapper()
            vacancy = invoice_line.timesheet.vacancy_offer.vacancy
            skill = vacancy.position
            activity_display_id = str(vacancy.id)[:30]
            position_parts = vacancy.position.name.split(' ')
            price_list = invoice.customer_company.price_lists.get(effective=True)
            rate = PriceListRate.objects.filter(price_list=price_list, skill=skill)
            name = ' '.join([part[:4] for part in position_parts])
            income_account_resp = self._get_object_by_field(
                '4-1000',
                resource=self.client.api.GeneralLedger.Account,
                single=True
            )

            data = activity_mapper.map_to_myob(
                activity_display_id,
                name[:30],
                ActivityMapper.TYPE_HOURLY,
                ActivityMapper.STATUS_CHARGEABLE,
                rate=rate,
                tax_code=tax_codes[invoice_line.vat.name],
                income_account=income_account_resp['UID'],
                description='{} {}'.format(vacancy.position, rate if rate else 'Base Rate')
            )
            activity_response = self._get_object_by_field(activity_display_id,
                                                          self.client.api.TimeBilling.Activity,
                                                          single=True)

            if not activity_response:
                self.client.api.TimeBilling.Activity.post(json=data, raw_resp=True)
                activity_response = self._get_object_by_field(activity_display_id,
                                                              self.client.api.TimeBilling.Activity,
                                                              single=True)

            activities.update({invoice_line.id: activity_response['UID']})

        return activities

    def _sync_to(self, invoice, sync_obj=None):
        tax_codes = self._get_tax_codes()
        params = {"$filter": "CompanyName eq '%s'" % invoice.customer_company.name}
        customer_data = self.client.api.Contact.Customer.get(params=params)
        customer_uid = customer_data['Items'][0]['UID']
        activities = self._create_or_update_activities(invoice, tax_codes)

        data = self.mapper.map_to_myob(invoice, customer_uid, tax_codes, activities)
        resp = self.resource.post(json=data, raw_resp=True)

        if 200 <= resp.status_code < 400:
            log.info('Invoice %s synced' % invoice.id)
        else:
            log.warning("[MYOB API] Invoice %s: %s", invoice.id, resp.text)
            return False

        return True
