import logging


log = logging.getLogger(__name__)


class BaseCategoryMixin:
    _base_category = None

    def _get_base_category(self):
        if self._base_category is None:
            base_category = self._get_object_by_field(
                'base hourly',
                resource=self.client.api.Payroll.PayrollCategory.Wage,
                myob_field='tolower(Name)'
            )
            if not base_category or not base_category['Count']:
                base_category = self._get_object_by_field(
                    'base hourly - workers',
                    resource=self.client.api.Payroll.PayrollCategory.Wage,
                    myob_field='tolower(Name)'
                )
            self._base_category = base_category
        return self._base_category


class StandardPayMixin:
    def _put_standart_pay_info(self, employee_item, candidate_contact=None):
        emp_uid = employee_item.get('EmployeePayrollDetails')
        if not emp_uid:
            return

        standard_pay = self.client.api.Contact.EmployeeStandardPay.get(
            uid=employee_item['EmployeeStandardPay']['UID']
        )

        if 'UID' not in standard_pay:
            return

        uid = standard_pay['UID']
        base_category = self._get_base_category()

        memo = None
        if candidate_contact is not None:
            contact = candidate_contact.contact
            memo = '{} {}'.format(contact.first_name, contact.last_name)

        pay_data = self.mapper.map_standard_pay(
            emp_uid.get('UID', ''),
            standard_pay.get('PayrollCategories', []),
            base_category=base_category,
            memo=memo
        )
        pay_data = self._get_data_to_update(standard_pay, pay_data)
        pay_data['Employee'] = {
            'UID': employee_item['UID']
        }

        resp = self.client.api.Contact.EmployeeStandardPay.put(
            uid=uid,
            json=pay_data,
            raw_resp=True
        )

        if resp.status_code >= 400:
            log.warning("[MYOB API] Standart Pay for %s: %s",
                        candidate_contact.id if candidate_contact else uid,
                        resp.text)
        else:
            log.info('Candidate Contact %s Standart Pay synced',
                     candidate_contact.id if candidate_contact else uid)


class CandidateCardFinderMixin:
    def _find_old_myob_card(self, candidate_contact, resource=None):
        contact = candidate_contact.contact
        resp = self.client.api.Contact.Employee.get(params={
            '$filter':
                "tolower(FirstName) eq '{first_name}' and tolower(LastName) eq '{last_name}'"
                .format(first_name=contact.first_name.replace("'", "''").lower(),
                        last_name=contact.last_name.replace("'", "''").lower())
        })

        if 'Errors' in resp:
            for error in resp['Errors']:
                log.warning('[MYOB API] find by name %s: %s', str(contact), error['Message'])
            return
        elif not resp['Count']:
            return

        return resp
