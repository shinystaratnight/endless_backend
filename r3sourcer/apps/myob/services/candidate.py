import logging

from r3sourcer.apps.candidate.models import SkillRel
from r3sourcer.apps.myob.mappers import CandidateMapper
from r3sourcer.apps.myob.services.base import BaseSync
from r3sourcer.apps.myob.services.mixins import BaseCategoryMixin, StandardPayMixin, CandidateCardFinderMixin


log = logging.getLogger(__name__)


class CandidateSync(BaseCategoryMixin,
                    StandardPayMixin,
                    CandidateCardFinderMixin,
                    BaseSync):
    app = "candidate"
    model = "CandidateContact"

    mapper_class = CandidateMapper

    def __init__(self, client, *args, **kwargs):
        super().__init__(client)

        self._superannuation_fund = {}
        self._expense_account = None
        self._base_category = None
        self._superannuation_category = None

    def _get_resource(self):
        return self.client.api.Contact.Employee

    def _sync_to(self, candidate_contact, sync_obj=None, partial=False):
        visa_type = candidate_contact.visa_type
        is_holiday_visa = visa_type and visa_type.subclass in ['417', '462']

        # get existing candidate data
        myob_card_number, old_myob_card_number, myob_contact_resp = self._get_myob_existing_resp(
            candidate_contact, candidate_contact.contact.get_myob_card_number(), sync_obj
        )

        new_card_number = None
        if is_holiday_visa:
            if myob_card_number.startswith('alttax'):
                new_card_number = myob_card_number
            else:
                new_card_number = 'alttax{}'.format(myob_card_number[:9])
            myob_contact_resp = self._get_object_by_field(new_card_number)

        data = self.mapper.map_to_myob(candidate_contact)
        if is_holiday_visa:
            notes = data.get('Notes', '')
            data['Notes'] = ('{}{}Working holiday visa'.format(notes, notes and '\r\n'))[:255]

        is_employee_exists = myob_contact_resp is not None and myob_contact_resp['Count']

        # create or update employee data on remote service
        if not is_employee_exists:
            data['DisplayID'] = new_card_number or myob_card_number
            resp = self.client.api.Contact.Employee.post(json=data, raw_resp=True)
        else:
            item = myob_contact_resp['Items'][0]
            data = self._get_data_to_update(item, data)
            resp = self.client.api.Contact.Employee.put(uid=item['UID'], json=data, raw_resp=True)

        if 200 <= resp.status_code < 400:
            log.info('Candidate Contact %s synced' % candidate_contact.id)

            self._update_sync_object(candidate_contact, new_card_number or old_myob_card_number)

            if not is_employee_exists:
                myob_contact_resp = self._get_object_by_field(new_card_number or myob_card_number)

                if not myob_contact_resp or not myob_contact_resp['Count']:
                    return

            item = myob_contact_resp['Items'][0]
            try:
                self._put_bank_account_info(item, candidate_contact)
            except ValueError as e:
                log.warning(
                    "[MYOB API] Cannot sync bank account for Candidate Contact %s. error: %s", candidate_contact.id, e
                )
            self._put_extra_data(item, candidate_contact)
            self._put_standart_pay_info(item, candidate_contact)
        else:
            log.warning("[MYOB API] Candidate Contact %s: %s",
                        candidate_contact.id,
                        resp.text)

    def _put_bank_account_info(self, employee_item, candidate_contact):
        payment_details = self.client.api.Contact.EmployeePaymentDetails.get(
            uid=employee_item['EmployeePaymentDetails']['UID']
        )

        if 'UID' not in payment_details:
            return

        uid = payment_details['UID']

        bank_data = self.mapper.map_bank_account(candidate_contact)
        bank_data = self._get_data_to_update(payment_details, bank_data)
        bank_data['Employee'] = {
            'UID': employee_item['UID'],
        }

        resp = self.client.api.Contact.EmployeePaymentDetails.put(uid=uid, json=bank_data, raw_resp=True)

        if resp.status_code >= 400:
            log.warning("[MYOB API] Bank Account for %s: %s",
                        candidate_contact.id,
                        resp.text)
        else:
            log.info('Candidate Contact %s Bank Account synced',
                     candidate_contact.id)

    def _put_extra_data(self, employee_item, candidate_contact):
        if not employee_item:
            return

        emp_uid = employee_item.get('EmployeePayrollDetails')
        if not emp_uid:
            return

        emp_uid = emp_uid.get('UID', '')
        payroll_details = self.client.api.Contact.EmployeePayrollDetails.get(uid=emp_uid, raw_resp=True)

        if payroll_details.status_code >= 400:
            return

        payroll_details = payroll_details.json()

        uid = payroll_details['UID']

        superannuation_fund = self._get_superannuation_fund(candidate_contact)
        superannuation_category = self._get_superannuation_category()

        # TODO: which expense_account we should use for candidate?
        expense_account = self._get_expense_account('6-5130')
        wage_categories = self._find_wage_categories(candidate_contact)
        if candidate_contact.visa_type and candidate_contact.visa_type.subclass in ['417', '462']:
            tax_table = self._get_tax_table('Withholding Variation')
            withholding_rate = 15
        else:
            tax_table = self._get_tax_table('Tax Free Threshold')
            withholding_rate = None

        for payroll_wage_cat in payroll_details['Wage']['WageCategories']:
            wage_categories.add(payroll_wage_cat['UID'])

        candidate_skill_rate = candidate_contact.candidate_skills.all().order_by('-hourly_rate').first()

        base_hourly_rate = candidate_skill_rate and candidate_skill_rate.hourly_rate

        data = self.mapper.map_extra_info(
            candidate_contact,
            expense_account=expense_account,
            superannuation_fund=superannuation_fund,
            wage_categories=wage_categories,
            tax_table=tax_table,
            withholding_rate=withholding_rate,
            superannuation_category=superannuation_category,
            base_hourly_rate=base_hourly_rate
        )
        data = self._get_data_to_update(payroll_details, data, deep=True)

        if superannuation_fund:
            data['Superannuation']['SuperannuationFund'] = {
                'UID': superannuation_fund['UID'],
            }

        data['Employee'] = {
            'UID': employee_item['UID'],
        }

        resp = self.client.api.Contact.EmployeePayrollDetails.put(uid=uid, json=data, raw_resp=True)

        if resp.status_code >= 400:
            log.warning("[MYOB API] extra data for %s: %s", candidate_contact.id, resp.text)
        else:
            log.info('Candidate Contact %s extra data synced', candidate_contact.id)

    def _get_superannuation_fund(self, candidate_contact):
        super_fund = candidate_contact.superannuation_fund
        fund_name = super_fund.product_name if super_fund else ''

        if not fund_name:
            return

        if fund_name not in self._superannuation_fund:
            resp = self._get_object_by_field(
                fund_name.lower(),
                resource=self.client.api.Payroll.SuperannuationFund,
                myob_field='tolower(Name)',
                single=True
            )

            if not resp:
                resp = self._get_object_by_field(
                    super_fund.fund_name.lower(),
                    resource=self.client.api.Payroll.SuperannuationFund,
                    myob_field='tolower(Name)',
                    single=True
                )

            self._superannuation_fund[fund_name] = resp

        return self._superannuation_fund[fund_name]

    def _get_superannuation_category(self):
        if self._superannuation_category is None:
            superannuation_category = self._get_object_by_field(
                'superannuation - labour',
                resource=self.client.api.Payroll.PayrollCategory.Superannuation,
                myob_field='tolower(Name)', single=True
            )
            if not superannuation_category:
                superannuation_category = self._get_object_by_field(
                    'superannuation guarantee',
                    resource=self.client.api.Payroll.PayrollCategory.Superannuation,
                    myob_field='tolower(Name)', single=True
                )
            self._superannuation_category = superannuation_category
        return self._superannuation_category

    def _get_expense_account(self, display_id):
        if not self._expense_account:
            resp = self.client.api.GeneralLedger.Account.get(params={'$filter': "DisplayID eq '%s'" % display_id})
            if resp and 'Errors' in resp:
                for error in resp['Errors']:
                    log.warning('[MYOB API] expense account %s error: %s', display_id, error['Message'])

                return

            if resp and resp['Count']:
                self._expense_account = resp['Items'][0]

        return self._expense_account

    def _find_wage_categories(self, candidate_contact):
        candidate_skill_rates = SkillRel.objects.filter(candidate_contact=candidate_contact, skill__active=True)

        wage_categories = set()

        base_category = self._get_base_category()
        if base_category and base_category['Count']:
            wage_categories.add(base_category['Items'][0]['UID'])

        for candidate_skill_rate in candidate_skill_rates:
            myob_id = candidate_skill_rate.get_myob_name()
            wage_category = self._get_wage_category(myob_id)

            if not wage_category:
                data = self.mapper.map_to_myob_wage_category(myob_id, candidate_skill_rate)
                resp = self.client.api.Payroll.PayrollCategory.Wage.post(json=data, raw_resp=True)

                if resp.status_code < 400:
                    wage_category = self._get_wage_category(myob_id)
                else:
                    log.warning('[MYOB API] sync wage category %s failed: %s', myob_id, resp.text)

            if wage_category:
                wage_categories.add(wage_category['UID'])

        return wage_categories

    def _get_wage_category(self, name):
        resp = self.client.api.Payroll.PayrollCategory.Wage.get(params={
            '$filter': "tolower(Name) eq '{}'".format(name[:31].strip().lower())
        })

        if resp and 'Count' in resp and resp['Count']:
            return resp['Items'][0]

    def _get_tax_table(self, name):
        tax_table = self._get_object_by_field(
            name.lower(),
            resource=self.client.api.Payroll.PayrollCategory.TaxTable,
            myob_field='tolower(Name)'
        )
        if not tax_table:
            resp = self.client.api.Payroll.PayrollCategory.Wage.get()
            return resp['Count'] and resp['Items'][0]
        return tax_table['Count'] and tax_table['Items'][0]
