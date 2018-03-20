import datetime
import logging

from django.utils import timezone

from r3sourcer.apps.activity.models import Activity
from r3sourcer.apps.myob.mappers import CompanyMapper, get_formatted_abn
from r3sourcer.apps.myob.models import MYOBSyncObject
from r3sourcer.apps.myob.services.base import BaseSync


log = logging.getLogger(__name__)


class CompanySync(BaseSync):

    app = "core"
    model = "Company"

    mapper_class = CompanyMapper

    def _get_resource(self):
        return self.client.api.Contact.Customer

    def _get_salesperson(self, portfolio_manager):
        myob_card_number = portfolio_manager.legacy_myob_card_number
        salesperson = None

        if myob_card_number:
            salesperson = self._get_object_by_field(
                myob_card_number, resource=self.client.api.Contact.Employee, single=True
            )

        if salesperson is None:
            contact = portfolio_manager.contact
            myob_card_number = contact.get_myob_card_number()

            candidate = getattr(contact, 'candidate_contacts', None)
            if candidate:
                model_parts = ['candidate', 'CandidateContact']
                sync_obj = MYOBSyncObject.objects.filter(
                    app=model_parts[0],
                    model=model_parts[1],
                    record=candidate.id,
                    account=self.account,
                    direction=MYOBSyncObject.SYNC_DIRECTION_CHOICES.myob
                ).first()

                old_myob_card_number = sync_obj and sync_obj.legacy_myob_card_number
                if old_myob_card_number:
                    myob_card_number = old_myob_card_number

            resp = self._get_object_by_field(myob_card_number, resource=self.client.api.Contact.Employee)
            if not resp or not resp['Count']:
                resp = self.client.api.Contact.Employee.get(params={
                    '$filter':
                        "tolower(FirstName) eq '{first_name}' and tolower(LastName) eq '{last_name}'"
                        .format(first_name=contact.first_name.replace("'", "''").lower(),
                                last_name=contact.last_name.replace("'", "''").lower())
                })

            if not resp or not resp['Count']:
                return self._sync_salesperson_employee(contact)

            if resp['Count'] == 1:
                salesperson = resp['Items'][0]
                if contact.get_myob_card_number() != salesperson['DisplayID']:
                    portfolio_manager.legacy_myob_card_number = salesperson['DisplayID']
                    portfolio_manager.save(update_fields=['legacy_myob_card_number'])
            else:
                starts_at = timezone.now()
                activity_values = {
                    'contact': contact,
                    'starts_at': starts_at,
                    'ends_at': starts_at + datetime.timedelta(days=1)
                }
                Activity.objects.create(**activity_values)

        return salesperson

    def _sync_salesperson_employee(self, contact):
        data = self.mapper._map_contact_to_myob(contact)

        data['DisplayID'] = contact.get_myob_card_number()
        data['IsIndividual'] = True
        resp = self.client.api.Contact.Employee.post(json=data, raw_resp=True)

        if 200 <= resp.status_code < 400:
            return self._get_object_by_field(
                contact.get_myob_card_number(),
                resource=self.client.api.Contact.Employee,
                single=True
            )

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
