import datetime
import mock
from decimal import Decimal

import stripe

from r3sourcer.apps.billing.models import Discount, Subscription, Payment, SubscriptionType
from r3sourcer.apps.billing.tasks import charge_for_extra_workers, charge_for_sms
from r3sourcer.apps.core.tasks import cancel_subscription_access


class TestSubscription:

    @mock.patch.object(stripe.Subscription, 'retrieve')
    def test_get_stripe_subscription(self, mocked_retrieve, subscription):
        """expect call retrieve to get Stripe subscription"""
        subscription.get_stripe_subscription()
        mocked_retrieve.assert_called_once_with(subscription.subscription_id)

    @mock.patch.object(stripe.Subscription, 'retrieve')
    def test_sync_status_to_incomplete_and_activate(self, mocked_retrieve, canceled_subscription):
        """expect call retrieve to get Stripe subscription and then change status to incomplete and activate"""
        assert canceled_subscription.status == 'canceled'

        stripe_subscription = mock.Mock()
        stripe_subscription.status = 'incomplete'
        mocked_retrieve.return_value = stripe_subscription

        canceled_subscription.sync_status()

        mocked_retrieve.assert_called_once_with(canceled_subscription.subscription_id)
        assert canceled_subscription.status == 'incomplete'
        assert canceled_subscription.active is True

    @mock.patch.object(stripe.Subscription, 'retrieve')
    def test_sync_status_to_active_and_activate(self, mocked_retrieve, canceled_subscription):
        """expect call retrieve to get Stripe subscription and then change status to active and activate"""
        assert canceled_subscription.status == 'canceled'

        stripe_subscription = mock.Mock()
        stripe_subscription.status = 'active'
        mocked_retrieve.return_value = stripe_subscription

        canceled_subscription.sync_status()

        mocked_retrieve.assert_called_once_with(canceled_subscription.subscription_id)
        assert canceled_subscription.status == 'active'
        assert canceled_subscription.active is True

    @mock.patch.object(stripe.Subscription, 'retrieve')
    def test_sync_status_to_trialing_and_activate(self, mocked_retrieve, canceled_subscription):
        """expect call retrieve to get Stripe subscription and then change status to trialing and activate"""
        assert canceled_subscription.status == 'canceled'

        stripe_subscription = mock.Mock()
        stripe_subscription.status = 'trialing'
        mocked_retrieve.return_value = stripe_subscription

        canceled_subscription.sync_status()

        mocked_retrieve.assert_called_once_with(canceled_subscription.subscription_id)
        assert canceled_subscription.status == 'trialing'
        assert canceled_subscription.active is True

    @mock.patch.object(stripe.Subscription, 'retrieve')
    def test_sync_status_to_not_allowed_and_deactivate(self, mocked_retrieve, subscription):
        """expect call retrieve to get Stripe subscription and then change status to past_due and deactivate"""
        assert subscription.status == 'active'
        assert subscription.active is True

        stripe_subscription = mock.Mock()
        stripe_subscription.status = 'past_due'
        mocked_retrieve.return_value = stripe_subscription

        subscription.sync_status()

        mocked_retrieve.assert_called_once_with(subscription.subscription_id)
        assert subscription.status == 'past_due'
        assert subscription.active is False

    @mock.patch.object(stripe.Subscription, 'retrieve')
    def test_sync_status_with_stripe_subscription(self, mocked_retrieve, subscription):
        """expect call retrieve to get Stripe subscription and then change status to canceled and deactivate"""
        assert subscription.status == 'active'
        assert subscription.active is True

        stripe_subscription = mock.Mock()
        stripe_subscription.status = 'canceled'

        subscription.sync_status(stripe_subscription=stripe_subscription)

        mocked_retrieve.assert_not_called()
        assert subscription.status == 'canceled'
        assert subscription.active is False

    def test_update_user_permissions_for_allowed_status(self):
        pass

    def test_update_user_permissions_for_not_allowed_status(self):
        pass

    @mock.patch.object(stripe.Subscription, 'retrieve')
    def test_sync_periods_with_stripe_subscription(self, mocked_retrieve, subscription):
        """expect not to call retrieve and change current_period dates"""
        stripe_subscription = mock.Mock()
        stripe_subscription.current_period_start = 1632375374
        stripe_subscription.current_period_end = 1634967374

        assert subscription.current_period_start is None
        assert subscription.current_period_end is None

        subscription.sync_periods(stripe_subscription)

        mocked_retrieve.assert_not_called()
        assert subscription.current_period_start is not None
        assert subscription.current_period_end is not None

    @mock.patch.object(stripe.Subscription, 'retrieve')
    def test_sync_periods_for_active_subscription(self, mocked_retrieve, subscription):
        """expect call retrieve to get Stripe subscription and then change current_period dates"""
        stripe_subscription = mock.Mock()
        stripe_subscription.current_period_start = 1632375374
        stripe_subscription.current_period_end = 1634967374
        mocked_retrieve.return_value = stripe_subscription

        assert subscription.current_period_start is None
        assert subscription.current_period_end is None

        subscription.sync_periods()

        mocked_retrieve.assert_called_once_with(subscription.subscription_id)
        assert subscription.current_period_start is not None
        assert subscription.current_period_end is not None

    @mock.patch.object(Subscription, 'save')
    @mock.patch.object(stripe.Subscription, 'retrieve')
    def test_sync_periods_for_inactive_subscription(self, mocked_retrieve, mock_save, canceled_subscription):
        """expect to not call retrieve or save"""
        canceled_subscription.sync_periods()

        mocked_retrieve.assert_not_called()
        mock_save.assert_not_called()

    @mock.patch.object(stripe.Subscription, 'retrieve')
    @mock.patch.object(stripe.Subscription, 'modify')
    @mock.patch.object(cancel_subscription_access, 'apply_async')
    def test_deactivate(self, mocked_apply_async, mocked_modify, mocked_retrieve, subscription):
        """expect call retrieve to get Stripe subscription and then modify without cancel_subscription_access"""
        stripe_subscription = mock.Mock()
        mocked_retrieve.return_value = stripe_subscription

        subscription.deactivate()

        mocked_retrieve.assert_called_once_with(subscription.subscription_id)
        stripe_subscription.modify.assert_called_once_with(subscription.subscription_id, cancel_at_period_end=True, prorate=False)
        mocked_apply_async.assert_not_called()

    @mock.patch.object(stripe.Subscription, 'retrieve')
    @mock.patch.object(stripe.Subscription, 'modify')
    @mock.patch.object(cancel_subscription_access, 'apply_async')
    def test_deactivate_with_stripe_subscription(self, mocked_apply_async, mocked_modify, mocked_retrieve, subscription):
        """expect call retrieve to get Stripe subscription and then modify without cancel_subscription_access"""
        stripe_subscription = mock.Mock()
        mocked_retrieve.return_value = stripe_subscription

        subscription.deactivate(stripe_subscription=stripe_subscription)

        mocked_retrieve.assert_not_called()
        stripe_subscription.modify.assert_called_once_with(subscription.subscription_id, cancel_at_period_end=True, prorate=False)
        mocked_apply_async.assert_not_called()

    def test_save_status(self, subscription):
        """change a status of subscription and expect it saves"""
        assert subscription.status == 'active'

        subscription.status = 'canceled'
        subscription.save(update_fields=['status'])

        assert subscription.status == 'canceled'

    @mock.patch.object(stripe.Subscription, 'retrieve')
    @mock.patch.object(stripe.Subscription, 'modify')
    def test_save_another_active_subscription(self, mocked_modify, mocked_retrieve, canceled_subscription, subscription):
        """make a canceled subscription active and expect that 'old' subscription become inactive"""
        assert subscription.status == 'active'
        assert subscription.active is True
        assert canceled_subscription.status == 'canceled'

        stripe_subscription = mock.Mock()
        mocked_retrieve.return_value = stripe_subscription

        canceled_subscription.status = 'active'
        canceled_subscription.active = True
        canceled_subscription.save(update_fields=['status', 'active'])
        mocked_retrieve.assert_called_once()
        stripe_subscription.modify.assert_called_once_with(subscription.subscription_id, cancel_at_period_end=True, prorate=False)

        subscription.refresh_from_db()
        assert subscription.status == 'canceled'
        assert subscription.active is False
        assert canceled_subscription.status == 'active'
        assert canceled_subscription.active is True


class TestSMSBalance:

    def test_substract_sms_cost(self, client, user, company, relationship):
        sms_balance = company.sms_balance
        sms_balance.balance = 100
        sms_balance.save()
        sms_balance.substract_sms_cost(3)

        assert sms_balance.balance == Decimal('99.76')

    def test_send_low_balance_notification(self, client, user, company, relationship, low_balance_limit):
        sms_balance = company.sms_balance
        sms_balance.balance = low_balance_limit.low_balance_limit - 1
        sms_balance.save()

        assert company.sms_balance.low_balance_sent is True

    def test_send_low_balance_notification_twice(self, client, user, company, relationship, low_balance_limit):
        sms_balance = company.sms_balance
        sms_balance.balance = low_balance_limit.low_balance_limit - 1
        sms_balance.save()

        assert company.sms_balance.low_balance_sent is True

        sms_balance.balance = low_balance_limit.low_balance_limit + 10
        sms_balance.save()

        assert company.sms_balance.low_balance_sent is False

    def test_send_ran_out_notification(self, client, user, company, relationship, ran_out_balance_limit):
        sms_balance = company.sms_balance
        sms_balance.balance = ran_out_balance_limit.low_balance_limit - 1
        sms_balance.save()

        assert company.sms_balance.ran_out_balance_sent is True

    def test_send_ran_out_notification_twice(self, client, user, company, relationship, ran_out_balance_limit):
        sms_balance = company.sms_balance
        sms_balance.balance = ran_out_balance_limit.low_balance_limit - 1
        sms_balance.save()

        assert company.sms_balance.ran_out_balance_sent is True

        sms_balance.balance = ran_out_balance_limit.low_balance_limit + 10
        sms_balance.save()

        assert company.sms_balance.ran_out_balance_sent is False

    def test_send_low_balance_general_company(self, client, user, regular_company, relationship,
                                                           low_balance_limit):
        sms_balance = regular_company.sms_balance
        sms_balance.balance = low_balance_limit.low_balance_limit - 1
        sms_balance.save()

        assert regular_company.sms_balance.low_balance_sent is False

    def test_charge_for_sms_withour_last_payment(self):
        pass

    def test_charge_for_sms_with_paid_last_payment(self):
        pass

    def test_charge_for_sms_with_not_paid_last_payment(self):
        pass

    def test_charge_for_sms_with_void_last_payment(self):
        pass


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
        charge_for_sms(100, company.sms_balance.id)

        assert Payment.objects.first().amount == 75

    @mock.patch.object(stripe.InvoiceItem, 'create')
    @mock.patch.object(stripe.Invoice, 'create')
    @mock.patch('r3sourcer.apps.core.models.Company.active_workers')
    def test_apply_discount_extra_workers(self, mocked_invoice_item, mocked_invoice, active_workers, client, user,
                                          company):
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
            subscription_type=SubscriptionType.objects.create(
                type='monthly'
            ),
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
