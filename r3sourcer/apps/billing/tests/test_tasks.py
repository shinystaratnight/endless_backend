import datetime
import mock

import stripe

from django.utils import timezone

from r3sourcer.apps.billing.tasks import charge_for_extra_workers, charge_for_sms
from r3sourcer.apps.billing.models import SMSBalance, Payment, Subscription
from r3sourcer.apps.candidate.models import CandidateContact
from r3sourcer.apps.core.models import User
from r3sourcer.apps.hr.models import JobOffer, TimeSheet


class TestActiveWorkers:
    def test_active_workers_zero(self, client, user, company, relationship):
        assert company.active_workers() == 0

    def test_active_workers(self, client, user, company, relationship, contact, shift):
        user2 = User.objects.create_user(
            email='test2@test.tt', phone_mobile='+12345678902',
            password='test1234'
        )
        contact2 = user2.contact
        cc1 = CandidateContact.objects.create(contact=contact)
        cc2 = CandidateContact.objects.create(contact=contact2)
        job_offer1 = JobOffer.objects.create(
            candidate_contact=cc1,
            shift=shift
        )
        job_offer2 = JobOffer.objects.create(
            candidate_contact=cc2,
            shift=shift
        )
        TimeSheet.objects.create(
            job_offer=job_offer1,
            shift_started_at=timezone.now()
        )
        TimeSheet.objects.create(
            job_offer=job_offer2,
            shift_started_at=timezone.now()
        )
        assert company.active_workers() == 2


class TestChargeForExtraWorkers:
    @mock.patch('r3sourcer.apps.core.models.Company.active_workers')
    def test_no_extra_workers(self, active_workers, client, user, company, relationship, contact, shift):
        active_workers.return_value = 100
        Subscription.objects.create(
            company=company,
            name='subscription',
            type='monthly',
            price=500,
            worker_count=100,
        )
        active_workers.return_value = 100
        charge_for_extra_workers()

        assert Payment.objects.count() == 0

    @mock.patch('r3sourcer.apps.core.models.Company.active_workers')
    def test_extra_workers(self, active_workers, client, user, company, relationship):
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

        assert Payment.objects.count() == 1
        assert Payment.objects.first().amount == 130

    @mock.patch('r3sourcer.apps.core.models.Company.active_workers')
    def test_extra_workers_annual_subscription(self, active_workers, client, user, company, relationship):
        active_workers.return_value = 110
        company.stripe_customer = 'cus_CnGRCuSr6Fo0Uv'
        company.save()
        Subscription.objects.create(
            company=company,
            name='subscription',
            type='annual',
            price=500,
            worker_count=100,
            active=True,
            current_period_end=datetime.date.today()
        )
        charge_for_extra_workers()

        assert Payment.objects.count() == 1
        assert Payment.objects.first().amount == 100


class TestChargeForSMS:
    @mock.patch.object(stripe.Charge, 'create')
    @mock.patch.object(Subscription, 'deactivate')
    def test_charge(self, mocked_deactivate, mocked_charge, client, user, company, relationship):
        mocked_value = mock.Mock()
        mocked_value.status = 'status'
        mocked_value.id = 'stripe_id'
        mocked_charge.return_value = mocked_value
        initial_payment_count = Payment.objects.count()
        sms_balance = SMSBalance.objects.create(company=company, balance=100)
        charge_for_sms(company.id, 100, sms_balance.id)

        assert initial_payment_count + 1 == Payment.objects.count()
