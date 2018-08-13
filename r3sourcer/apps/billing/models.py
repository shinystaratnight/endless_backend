import datetime

import stripe

from decimal import Decimal
from django.conf import settings
from django.db import models
from model_utils import Choices

from r3sourcer.apps.core.models import Company


stripe.api_key = settings.STRIPE_SECRET_API_KEY


class Subscription(models.Model):
    SUBSCRIPTION_TYPES = Choices(
        ('annual', 'Annual'),
        ('monthly', 'Monthly')
    )
    SUBSCRIPTION_STATUSES = Choices(
        ('active', 'Active'),
        ('past_due', 'Past due'),
        ('canceled', 'Canceled'),
        ('unpaid', 'Unpaid'),
    )
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='subscriptions')
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255, choices=SUBSCRIPTION_TYPES)
    price = models.PositiveIntegerField()
    worker_count = models.PositiveIntegerField()
    created = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)
    status = models.CharField(max_length=255, choices=SUBSCRIPTION_STATUSES)
    current_period_start = models.DateTimeField(blank=True, null=True)
    current_period_end = models.DateTimeField(blank=True, null=True)

    # stripe ids
    plan_id = models.CharField(max_length=255)
    subscription_id = models.CharField(max_length=255)

    def sync_status(self):
        subscription = stripe.Subscription.retrieve(self.subscription_id)
        self.status = subscription.status

    def sync_periods(self):
        subscription = stripe.Subscription.retrieve(self.subscription_id)
        self.current_period_start = datetime.datetime.fromtimestamp(subscription.current_period_start)
        self.current_period_end = datetime.datetime.fromtimestamp(subscription.current_period_end)

    def deactivate(self):
        sub = stripe.Subscription.retrieve(self.subscription_id)
        sub.delete(at_period_end=True)

    @property
    def last_time_billed(self):
        last_payment = self.company.payment_set.order_by('-created').first()

        if last_payment:
            return last_payment.created

    def save(self, *args, **kwargs):
        super(Subscription, self).save(*args, **kwargs)

        if self.active:
            subscriptions = Subscription.objects.filter(company=self.company) \
                                                .exclude(id=self.id)

            for subscription in subscriptions:
                subscription.deactivate()
                subscription.active = False
                subscription.save()


class SMSBalance(models.Model):
    company = models.OneToOneField('core.Company', blank=True, null=True, related_name='sms_balance')
    balance = models.DecimalField(default=0, max_digits=8, decimal_places=2)
    top_up_amount = models.IntegerField(default=100)
    top_up_limit = models.IntegerField(default=10)
    last_payment = models.ForeignKey('Payment', blank=True, null=True)

    def substract_sms_cost(self, number_of_segments):
        amount = number_of_segments * settings.COST_OF_SMS_SEGMENT
        self.balance = self.balance - amount
        self.save()

    def save(self, *args, **kwargs):
        from r3sourcer.apps.billing.tasks import charge_for_sms

        if self.balance <= self.top_up_limit:
            charge_for_sms.delay(self.company.id, self.top_up_amount, self.id)

        if Decimal(self.balance) - Decimal(settings.COST_OF_SMS_SEGMENT) < 0:
            self.company.sms_enabled = False
            self.company.save()

        if not self.company.sms_enabled and Decimal(self.balance) - Decimal(settings.COST_OF_SMS_SEGMENT) > 0:
            self.company.sms_enabled = True
            self.company.save()

        super(SMSBalance, self).save(*args, **kwargs)


class Payment(models.Model):
    PAYMENT_TYPES = Choices(
        ('sms', 'SMS'),
        ('extra_workers', 'Extra Workers'),
        ('subscription', 'Subscription'),
        ('candidate', 'Candidate Profile'),
    )
    PAYMENT_STATUSES = Choices(
        ('paid', 'Paid'),
        ('not_paid', 'Not paid')
    )
    company = models.ForeignKey(Company)
    type = models.CharField(max_length=255, choices=PAYMENT_TYPES)
    created = models.DateTimeField(auto_now_add=True)
    amount = models.IntegerField()
    status = models.CharField(max_length=255, choices=PAYMENT_STATUSES, default=PAYMENT_STATUSES.not_paid)
    stripe_id = models.CharField(max_length=255)
    invoice_url = models.CharField(max_length=255, blank=True, null=True)


class Discount(models.Model):
    DURATIONS = Choices(
        ('forever', 'Forever'),
        ('once', 'Once'),
        ('repeating', 'Repeating')
    )
    PAYMENT_TYPES = Choices(
        ('sms', 'SMS'),
        ('extra_workers', 'Extra Workers'),
        ('subscription', 'Subscription')
    )
    company = models.ForeignKey(Company, related_name='discounts')
    payment_type = models.CharField(max_length=255, choices=PAYMENT_TYPES, blank=True, null=True)
    percent_off = models.IntegerField(blank=True, null=True)
    amount_off = models.IntegerField(blank=True, null=True)
    active = models.BooleanField(default=True)
    duration = models.CharField(max_length=255, choices=DURATIONS)
    duration_in_months = models.IntegerField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    def apply_discount(self, original_amount):
        if self.percent_off:
            discounted_value = original_amount * (1.0 - (float(self.percent_off) / 100))
        else:
            discounted_value = original_amount - self.amount_off

        if self.duration == self.DURATIONS.once:
            self.active = False
            self.save()

        if self.duration == self.DURATIONS.repeating and self.duration_in_months:
            duration_in_days = 30 * self.duration_in_months

            if self.created + datetime.timedelta(days=duration_in_days) < datetime.datetime.now():
                self.active = False
                self.save()

        return discounted_value

    def save(self, *args, **kwargs):
        if not self.id and self.payment_type == 'subscription':
            subscription = Subscription.objects.get(company=self.company, active=True)

            coupon_data = {
                'duration': self.duration,
            }

            if self.percent_off:
                coupon_data.update({
                    'percent_off': self.percent_off,
                })
            else:
                coupon_data.update({
                    'amount_off': self.amount_off,
                    'currency': self.company.currency
                })

            if self.duration_in_months:
                coupon_data.update({
                    'duration_in_months': self.duration_in_months
                })

            coupon = stripe.Coupon.create(**coupon_data)
            subscription = stripe.Subscription.retrieve(subscription.subscription_id)
            subscription.coupon = coupon.id
            subscription.save()
        super(Discount, self).save(*args, **kwargs)
