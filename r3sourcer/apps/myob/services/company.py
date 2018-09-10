import logging

from r3sourcer.apps.myob.mappers import CompanyMapper, get_formatted_abn
from r3sourcer.apps.myob.services.base import BaseSync
from r3sourcer.apps.myob.services.mixins import SalespersonMixin


log = logging.getLogger(__name__)


class CompanySync(SalespersonMixin, BaseSync):

    app = "core"
    model = "Company"

    mapper_class = CompanyMapper

    def _get_resource(self):
        return self.client.api.Contact.Customer

    def _find_old_myob_card(self, company, resource=None):
        resp = self._get_object_by_field(
            get_formatted_abn(company.business_id),
            myob_field='SellingDetails/ABN'
        )

        if resp is None or not resp['Count']:
            resp = self._get_object_by_field(company.name.lower(),
                                             myob_field='tolower(CompanyName)')
        return resp

    def _sync_to(self, company, sync_obj=None):
        myob_card_number, old_myob_card_number, myob_client_resp = self._get_myob_existing_resp(
            company, company.get_myob_card_number(), sync_obj
        )

        tax_code = 'GST' if company.registered_for_gst else 'GNR'
        tax_code_resp = self._get_tax_code(tax_code)
        if not tax_code_resp:
            log.warning('[MYOB API] tax code %s: not found', tax_code)
            return

        salesperson = None
        portfolio_manager = company.get_portfolio_manager()
        if portfolio_manager:
            salesperson = self._get_salesperson(portfolio_manager)

        account_code = '4-1000'
        income_account_resp = self._get_object_by_field(
            account_code, resource=self.client.api.GeneralLedger.Account, single=True
        )

        data = self.mapper.map_to_myob(
            company, tax_code=tax_code_resp, salesperson=salesperson, income_account=income_account_resp
        )

        if myob_client_resp is None or not myob_client_resp['Count']:
            data['DisplayID'] = myob_card_number
            resp = self.client.api.Contact.Customer.post(json=data, raw_resp=True)
        else:
            item = myob_client_resp['Items'][0]
            data = self._get_data_to_update(item, data)
            printed_form = item['SellingDetails'].get('PrintedForm')
            if printed_form:
                data['SellingDetails']['PrintedForm'] = printed_form
            resp = self.client.api.Contact.Customer.put(uid=item['UID'], json=data, raw_resp=True)

        if 200 <= resp.status_code < 400:
            log.info('Company %s synced' % company.id)

            self._update_sync_object(company, old_myob_card_number)
        else:
            log.warning("[MYOB API] Company %s: %s", company.id, resp.text)
