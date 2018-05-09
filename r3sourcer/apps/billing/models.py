import datetime

import stripe

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
    company = models.ForeignKey(Company, related_name='subscriptions')
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255, choices=SUBSCRIPTION_TYPES)
    price = models.PositiveIntegerField()
    worker_count = models.PositiveIntegerField()
    created = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)
    status = models.CharField(max_length=255, choices=SUBSCRIPTION_STATUSES)
    current_period_start = models.DateField(blank=True, null=True)
    current_period_end = models.DateField(blank=True, null=True)

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

    def save(self, *args, **kwargs):
        super(Subscription, self).save(*args, **kwargs)

        if self.active:
            Subscription.objects.filter(company=self.company) \
                        .exclude(id=self.id) \
                        .update(active=False)


class SMSBalance(models.Model):
    company = models.ForeignKey(Company)
    balance = models.DecimalField(default=0, max_digits=8, decimal_places=2)
    top_up_amount = models.IntegerField(default=100)
    top_up_limit = models.IntegerField(default=10)
    discount = models.IntegerField(default=0)

    def substract_sms_cost(self, number_of_segments):
        amount = number_of_segments * settings.COST_OF_SMS_SEGMENT * (1.0 - (float(self.discount) / 100))
        self.balance = self.balance - amount
        self.save()

    def save(self, *args, **kwargs):
        from r3sourcer.apps.billing.tasks import charge_for_sms

        if self.balance <= self.top_up_limit:
            charge_for_sms.delay(self.company.id, self.top_up_amount, self.id)
            self.balance += self.top_up_amount

        super(SMSBalance, self).save(*args, **kwargs)


class Payment(models.Model):
    PAYMENT_TYPES = Choices(
        ('sms', 'SMS'),
        ('extra_workers', 'Extra Workers')
    )
    type = models.CharField(max_length=255, choices=PAYMENT_TYPES)
    created = models.DateTimeField(auto_now_add=True)
    amount = models.IntegerField()
    status = models.CharField(max_length=255)
    stripe_id = models.CharField(max_length=255)
