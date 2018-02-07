from datetime import timedelta, date
from decimal import Decimal

import mock
import pytest

from django_mock_queries.query import MockSet

from r3sourcer.apps.core.models import InvoiceRule, VAT
from r3sourcer.apps.hr.payment import InvoiceService
from r3sourcer.apps.hr.models import TimeSheet
from r3sourcer.apps.pricing.services import PriceListCoefficientService


today = date(2017, 1, 2)


@pytest.mark.django_db
class TestInvoiceService:

    @pytest.fixture
    def service(self):
        return InvoiceService()

    def test_get_price_list_rate(self, price_list_rate, service, skill,
                                 master_company, industry):
        res = service._get_price_list_rate(skill, master_company, industry)

        assert res == price_list_rate

    def test_get_price_list_rate_industry(
            self, industry_price_list_rate, service, skill, master_company,
            industry):

        res = service._get_price_list_rate(skill, master_company, industry)

        assert res == industry_price_list_rate

    @mock.patch.object(InvoiceService, 'generate_pdf')
    @mock.patch.object(InvoiceService, 'calculate')
    def test_prepare_invoice(self, mock_calc, mock_pdf, service,
                             master_company, vat):
        mock_calc.return_value = [{
            'date': date(2017, 1, 1),
            'units': Decimal(1),
            'notes': 'notes',
            'unit_price': Decimal(10),
            'amount': Decimal(10),
            'vat': VAT.objects.get(name='GST'),
        }], ['jobsite']

        res = service._prepare_invoice(master_company)

        assert res.total == Decimal(10)
        assert res.invoice_lines.count() == 1

    @mock.patch.object(InvoiceService, 'calculate')
    def test_prepare_invoice_no_lines(self, mock_calc, service,
                                      master_company):
        mock_calc.return_value = [], []

        res = service._prepare_invoice(master_company)

        assert res is None

    @mock.patch.object(PriceListCoefficientService, 'calc_company')
    @mock.patch('r3sourcer.apps.hr.payment.invoices.calc_worked_delta')
    @mock.patch.object(InvoiceService, '_get_price_list_rate')
    @mock.patch.object(InvoiceService, '_get_timesheets')
    def test_calculate(
            self, mock_timesheets, mock_price_list_rate, mock_worked, mock_pl,
            service, master_company, timesheet_approved, price_list_rate,
            rate_coefficient, vat):

        mock_timesheets.return_value = [timesheet_approved]
        mock_price_list_rate.return_value = price_list_rate
        mock_worked.return_value = timedelta(hours=8)
        mock_pl.return_value = [
            {'coefficient': rate_coefficient, 'hours': timedelta(hours=1)},
            {'coefficient': 'base', 'hours': timedelta(hours=7)},
        ]

        res, jobsites = service.calculate(master_company)

        assert len(res) == 2
        assert res[0]['amount'] == Decimal(20)
        assert res[1]['amount'] == Decimal(70)
        assert len(jobsites) == 1

    @mock.patch.object(PriceListCoefficientService, 'calc_company')
    @mock.patch('r3sourcer.apps.hr.payment.invoices.calc_worked_delta')
    @mock.patch.object(InvoiceService, '_get_price_list_rate')
    @mock.patch.object(InvoiceService, '_get_timesheets')
    def test_calculate_show_candidate(
            self, mock_timesheets, mock_price_list_rate, mock_worked, mock_pl,
            service, master_company, timesheet_approved, price_list_rate,
            rate_coefficient, vat):

        mock_timesheets.return_value = [timesheet_approved]
        mock_price_list_rate.return_value = price_list_rate
        mock_worked.return_value = timedelta(hours=8)
        mock_pl.return_value = [
            {'coefficient': rate_coefficient, 'hours': timedelta(hours=1)},
            {'coefficient': 'base', 'hours': timedelta(hours=7)},
        ]

        res, jobsites = service.calculate(master_company, show_candidate=True)

        assert len(res) == 2
        assert res[0]['amount'] == Decimal(20)
        assert res[1]['amount'] == Decimal(70)
        assert len(jobsites) == 1

    @mock.patch.object(InvoiceService, '_get_timesheets')
    def test_calculate_no_timesheets(
            self, mock_timesheets, service, master_company):

        mock_timesheets.return_value = []

        res, jobsites = service.calculate(master_company)

        assert len(res) == 0

    @mock.patch.object(InvoiceService, '_prepare_invoice')
    @mock.patch('r3sourcer.apps.hr.payment.invoices.get_invoice_rule')
    @mock.patch.object(InvoiceService, 'calculate')
    def test_prepare(self, mock_calc, mock_invoice_rule, mock_prepare_invoice,
                     service, master_company, invoice_rule_master_company):

        mock_calc.return_value = [], []
        mock_invoice_rule.return_value = invoice_rule_master_company

        service.prepare(master_company, today)

        mock_prepare_invoice.assert_called_with(
            master_company, today, show_candidate=False
        )

    @mock.patch.object(InvoiceService, '_prepare_invoice')
    @mock.patch('r3sourcer.apps.hr.payment.invoices.get_invoice_rule')
    @mock.patch.object(InvoiceService, 'calculate')
    def test_prepare_invoice_exists(
            self, mock_calc, mock_invoice_rule, mock_prepare_invoice, service,
            master_company, invoice_rule_master_company, invoice):

        mock_calc.return_value = [], []
        mock_invoice_rule.return_value = invoice_rule_master_company

        service.prepare(master_company, today)

        mock_prepare_invoice.assert_called_with(
            master_company, date(2017, 1, 2), show_candidate=False
        )

    @mock.patch.object(TimeSheet, 'objects', new_callable=mock.PropertyMock)
    @mock.patch.object(InvoiceService, '_prepare_invoice')
    @mock.patch('r3sourcer.apps.hr.payment.invoices.get_invoice_rule')
    @mock.patch.object(InvoiceService, 'calculate')
    def test_prepare_per_jobsite(
            self, mock_calc, mock_invoice_rule, mock_prepare_invoice,
            mock_timesheets, master_company, invoice_rule_master_company,
            timesheet_approved, jobsite, service):

        invoice_rule_master_company.separation_rule = \
            InvoiceRule.SEPARATION_CHOICES.per_jobsite
        mock_calc.return_value = [], []
        mock_invoice_rule.return_value = invoice_rule_master_company
        mock_timesheets.return_value.filter.return_value = [timesheet_approved]

        service.prepare(master_company, today)

        mock_prepare_invoice.assert_called_with(
            master_company, today, [timesheet_approved], show_candidate=False
        )

    @mock.patch.object(InvoiceService, '_prepare_invoice')
    @mock.patch('r3sourcer.apps.hr.payment.invoices.get_invoice_rule')
    @mock.patch.object(InvoiceService, 'calculate')
    def test_prepare_per_jobsite_no_jobsite(
            self, mock_calc, mock_invoice_rule, mock_prepare_invoice, service,
            master_company, invoice_rule_master_company):

        invoice_rule_master_company.separation_rule = \
            InvoiceRule.SEPARATION_CHOICES.per_jobsite
        mock_calc.return_value = [], []
        mock_invoice_rule.return_value = invoice_rule_master_company

        service.prepare(master_company, today)

        assert not mock_prepare_invoice.called

    @mock.patch.object(TimeSheet, 'objects', new_callable=mock.PropertyMock)
    @mock.patch.object(InvoiceService, '_get_timesheets')
    @mock.patch.object(InvoiceService, '_prepare_invoice')
    @mock.patch('r3sourcer.apps.hr.payment.invoices.get_invoice_rule')
    @mock.patch.object(InvoiceService, 'calculate')
    def test_prepare_per_candidate(
            self, mock_calc, mock_invoice_rule, mock_prepare_invoice,
            mock_get_ts, mock_timesheets, master_company, timesheet_approved,
            invoice_rule_master_company, candidate_contact, service):

        invoice_rule_master_company.separation_rule = \
            InvoiceRule.SEPARATION_CHOICES.per_candidate
        mock_calc.return_value = [], []
        mock_invoice_rule.return_value = invoice_rule_master_company
        mock_timesheets.return_value.filter.return_value = [timesheet_approved]
        mock_get_ts.return_value = MockSet(timesheet_approved)

        service.prepare(master_company, today)

        mock_prepare_invoice.assert_called_with(
            master_company, today, [timesheet_approved], show_candidate=False
        )

    @mock.patch.object(InvoiceService, '_prepare_invoice')
    @mock.patch('r3sourcer.apps.hr.payment.invoices.get_invoice_rule')
    @mock.patch.object(InvoiceService, 'calculate')
    def test_prepare_per_candidate_no_candidates(
            self, mock_calc, mock_invoice_rule, mock_prepare_invoice, service,
            master_company, invoice_rule_master_company):

        invoice_rule_master_company.separation_rule = \
            InvoiceRule.SEPARATION_CHOICES.per_candidate
        mock_calc.return_value = [], []
        mock_invoice_rule.return_value = invoice_rule_master_company

        service.prepare(master_company, today)

        assert not mock_prepare_invoice.called
