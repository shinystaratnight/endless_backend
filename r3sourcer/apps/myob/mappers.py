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

    def map_to_myob(self, invoice, tax, account_debit, account_tax,
                    account_credit):
        data = {
            'DateOccurred': format_date_to_myob(invoice.date),
            'IsTaxInclusive': False,
            'IsYearEndAdjustment': False,
        }

        lines = [{
            'Account': {'UID': account_debit['UID']},
            'TaxCode': {'UID': tax['UID']},
            'Amount': invoice.total_with_tax,
            'IsCredit': False
        }, {
            'Account': {'UID': account_credit['UID']},
            'TaxCode': {'UID': tax['UID']},
            'Amount': invoice.total,
            'IsCredit': True
        }, {
            'Account': {'UID': account_tax['UID']},
            'TaxCode': {'UID': tax['UID']},
            'Amount': invoice.tax,
            'IsCredit': True
        }]

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
