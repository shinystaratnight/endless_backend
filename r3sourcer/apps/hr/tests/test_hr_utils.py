import pytest
import freezegun
from datetime import datetime, date, timedelta
from django.utils import timezone

from r3sourcer.apps.core.models import InvoiceRule
from r3sourcer.apps.hr.models import PayslipRule
from r3sourcer.apps.hr.utils.utils import (
    today_5_am, today_7_am, today_12_pm, today_12_30_pm, today_3_30_pm,
    tomorrow, tomorrow_5_am, tomorrow_7_am, tomorrow_end_5_am, _time_diff,
    get_invoice_rule, get_payslip_rule
)


fun_test_data = [
    (today_5_am, timezone.make_aware(datetime(2017, 1, 1, 5, 0))),
    (today_7_am, timezone.make_aware(datetime(2017, 1, 1, 7, 0))),
    (today_12_pm, timezone.make_aware(datetime(2017, 1, 1, 12, 0))),
    (today_12_30_pm, timezone.make_aware(datetime(2017, 1, 1, 12, 30))),
    (today_3_30_pm, timezone.make_aware(datetime(2017, 1, 1, 15, 30))),
    (tomorrow, date(2017, 1, 2)),
    (tomorrow_5_am, timezone.make_aware(datetime(2017, 1, 2, 5, 0))),
    (tomorrow_7_am, timezone.make_aware(datetime(2017, 1, 2, 7, 0))),
    (tomorrow_end_5_am, timezone.make_aware(datetime(2017, 1, 3, 5, 0))),
]


class TestUtils:

    @pytest.mark.parametrize(['fun', 'res'], fun_test_data)
    def test_date_and_time_functions(self, fun, res):
        with freezegun.freeze_time(datetime(2017, 1, 1, 0, 0, 0)):
            assert fun() == res

    @freezegun.freeze_time(datetime(2017, 1, 1, 0, 0, 0))
    def test_time_diff(self):
        now = datetime.now()
        assert _time_diff(now, now + timedelta(hours=8)) == timedelta(hours=8)

    def test_get_invoice_rule(self, regular_company):

        res = get_invoice_rule(regular_company)

        assert res == regular_company.invoice_rules.first()

    def test_get_invoice_rule_master(
            self, master_company, regular_company, company_rel):

        regular_company.invoice_rules.all().delete()
        res = get_invoice_rule(regular_company)

        assert res == master_company.invoice_rules.first()

    def test_get_invoice_rule_master_do_not_have_rule(
            self, master_company, regular_company, company_rel):

        InvoiceRule.objects.all().delete()
        res = get_invoice_rule(regular_company)

        assert res is None

    def test_get_invoice_rule_do_not_have_rule(self, regular_company,
                                               company_rel):

        InvoiceRule.objects.all().delete()
        res = get_invoice_rule(regular_company)

        assert res is None

    def test_get_payslip_rule(self, regular_company):

        res = get_payslip_rule(regular_company)

        assert res == regular_company.payslip_rules.first()

    def test_get_payslip_rule_master(
            self, master_company, regular_company, company_rel):

        regular_company.payslip_rules.all().delete()
        res = get_payslip_rule(regular_company)

        assert res == master_company.payslip_rules.first()

    def test_get_payslip_rule_master_do_not_have_rule(
            self, master_company, regular_company, company_rel):

        PayslipRule.objects.all().delete()
        res = get_payslip_rule(regular_company)

        assert res is None

    def test_get_payslip_rule_do_not_have_rule(self, regular_company,
                                               company_rel):

        PayslipRule.objects.all().delete()
        res = get_payslip_rule(regular_company)

        assert res is None
