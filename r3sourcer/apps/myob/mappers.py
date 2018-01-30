from datetime import datetime
from django.conf import settings

from django.utils import timezone
from django.utils.formats import date_format


def format_date_to_myob(date_time, only_date=False):
    if isinstance(date_time, datetime):
        try:
            date_time = timezone.make_naive(date_time)
        except ValueError:
            pass
        date_time = date_time.date()
    return date_time and date_format(date_time, settings.DATE_MYOB_FORMAT)


class InvoiceMapper:
    def map_to_myob(self, invoice, customer_uid, tax_codes, activities):
        data = {
            "Date": format_date_to_myob(invoice.date),
            "Customer": {'UID': customer_uid},
            "TotalTax": invoice.tax,
            "TotalAmount": invoice.total_with_tax
        }
        lines = list()

        for invoice_line in invoice.invoice_lines.all():
            lines.append({
                "Hours": invoice_line.units,
                "Rate": invoice_line.unit_price,
                "Total": invoice_line.amount,
                "Description": invoice_line.notes,
                "TaxCode": {"UID": tax_codes[invoice_line.vat.name]},
                "Activity": {"UID": activities[invoice_line.id]}
            })

        data['Lines'] = lines

        return data


class PayslipMapper:

    def map_to_myob(self, payslip, tax, account_wages, account_pay,
                    account_payg=None, account_superann_debit=None,
                    account_superann_credit=None):
        data = {
            'DateOccurred': format_date_to_myob(payslip.payment_date),
            'IsTaxInclusive': False,
            'IsYearEndAdjustment': False,
        }

        lines = [{
            'Account': {'UID': account_pay['UID']},
            'TaxCode': {'UID': tax['UID']},
            'Amount': payslip.get_gross_pay(),
            'IsCredit': True,
        }, {
            'Account': {'UID': account_wages['UID']},
            'TaxCode': {'UID': tax['UID']},
            'Amount': payslip.get_wage_pay(),
            'IsCredit': False
        }]

        if account_payg:
            lines.append({
                'Account': {'UID': account_payg['UID']},
                'TaxCode': {'UID': tax['UID']},
                'Amount': payslip.get_payg_pay(),
                'IsCredit': True
            })

        if account_superann_debit and account_superann_credit:
            lines.extend([{
                'Account': {'UID': account_superann_credit['UID']},
                'TaxCode': {'UID': tax['UID']},
                'Amount': payslip.get_superannuation_pay(),
                'IsCredit': True
            }, {
                'Account': {'UID': account_superann_debit['UID']},
                'TaxCode': {'UID': tax['UID']},
                'Amount': payslip.get_superannuation_pay(),
                'IsCredit': False
            }])

        data['Lines'] = lines

        return data


class ActivityMapper:
    TYPE_HOURLY = 'Hourly'
    TYPE_NON_HOURLY = 'NonHourly'

    STATUS_CHARGEABLE = 'Chargeable'
    STATUS_NON_CHARGEABLE = 'NonChargeable'

    TYPES = (TYPE_HOURLY, TYPE_NON_HOURLY)
    STATUSES = (STATUS_CHARGEABLE, STATUS_NON_CHARGEABLE)

    def map_to_myob(self, display_id, name, activity_type=TYPE_NON_HOURLY,
                    status=STATUS_NON_CHARGEABLE, income_account=None,
                    tax_code=None, rate=None, description=None):
        if activity_type not in self.TYPES or status not in self.STATUSES:
            return {}

        data = {
            'DisplayID': display_id[:30],
            'Type': activity_type,
            'Status': status,
            'Name': name,
        }
        if description:
            data['Description'] = description[:255]

        if activity_type != self.TYPE_HOURLY:
            data['UnitOfMeasurement'] = 'Irregular'
        else:
            if not income_account or not tax_code:
                return {}
            data['ChargeableDetails'] = {
                'IncomeAccount': {
                    'UID': income_account
                },
                'TaxCode': {
                    'UID': tax_code
                }
            }

            if rate:
                data['ChargeableDetails'].update({
                    'Rate': 'ActivityRate',
                    'ActivityRateExcludingTax': "{0:.2f}".format(rate)
                })

        return data