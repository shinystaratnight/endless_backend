import datetime
import mock

import stripe

from r3sourcer.apps.billing.models import Discount, Subscription, Payment
from r3sourcer.apps.billing.tasks import charge_for_extra_workers, charge_for_sms


class TestSMSBalance:
    def test_substract_sms_cost(self, client, user, company, relationship):
        sms_balance = company.sms_balance
        sms_balance.balance = 100
        sms_balance.save()
        sms_balance.substract_sms_cost(3)

        assert sms_balance.balance == 99.76


class TestDiscount:

    def test_apply_discount_percent_off(self, client, user, company):
        discount = Discount.objects.create(
            company=company,
            payment_type='sms',
            percent_off=25,
            duration='once',
        )

        assert discount.apply_discount(1000) == 750

    def test_apply_discount_amount_off(self, client, user, company):
        discount = Discount.objects.create(
            company=company,
            payment_type='sms',
            amount_off=25,
            duration='once',
        )

        assert discount.apply_discount(1000) == 975

    @mock.patch.object(stripe.InvoiceItem, 'create')
    @mock.patch.object(stripe.Invoice, 'create')
    @mock.patch.object(Subscription, 'deactivate')
    def test_apply_discount_sms(self, mocked_invoice_item, mocked_invoice, mocked_subscription, client, user, company, relationship):
        Discount.objects.create(
            company=company,
            payment_type='sms',
            amount_off=25,
            duration='once',
        )

        mocked_value = {'id': 'stripe_id'}
        mocked_invoice.return_value = mocked_value
        charge_for_sms(company.id, 100, company.sms_balance.id)

        assert Payment.objects.first().amount == 75

    @mock.patch('r3sourcer.apps.core.models.Company.active_workers')
    def test_apply_discount_extra_workers(self, active_workers, client, user, company):
        Discount.objects.create(
            company=company,
            payment_type='extra_workers',
            amount_off=30,
            duration='once',
        )
        active_workers.return_value = 110
        company.stripe_customer = 'cus_CnGRCuSr6Fo0Uv'
        company.save()
        Subscription.objects.create(
            company=company,
            name='subscription',
            type='monthly',
            price=500,
            worker_count=100,
            active=True,
            current_period_end=datetime.date.today()
        )
        charge_for_extra_workers()

        assert Payment.objects.first().amount == 100

    def test_duration_once(self, client, user, company):
        discount = Discount.objects.create(
            company=company,
            payment_type='sms',
            amount_off=25,
            duration='once',
        )
        discount.apply_discount(1000)

        assert not discount.active
