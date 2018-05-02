import stripe

from django.conf import settings
from django.db import models
from model_utils import Choices

from r3sourcer.apps.core.models import Company


stripe.api_key = settings.STRIPE_SECRET_API_KEY


class PaymentInformation(models.Model):
    company = models.ForeignKey(Company)
    email = models.CharField(max_length=255)
    token_type = models.CharField(max_length=255)
    token = models.CharField(max_length=255)

    def __str__(self, *args, **kwargs):
        return self.email


# TODO: Rename to subscription
class Plan(models.Model):
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
    company = models.ForeignKey(Company)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255, choices=SUBSCRIPTION_TYPES)
    price = models.PositiveIntegerField()
    worker_count = models.PositiveIntegerField()
    created = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)
    status = models.CharField(max_length=255, choices=SUBSCRIPTION_STATUSES)

    # stripe ids
    stripe_id = models.CharField(max_length=255)  # TODO: rename it to plan_id
    subscription_id = models.CharField(max_length=255)

    def sync_status(self):
        subscription = stripe.Subscription.retrieve(self.subscription_id)
        self.status = subscription.status
        self.save()

    def save(self, *args, **kwargs):
        super(Plan, self).save(*args, **kwargs)

        if self.active:
            Plan.objects.filter(company=self.company) \
                        .exclude(id=self.id) \
                        .update(active=False)


class SMSBalance(models.Model):
    balance = models.IntegerField(default=0)
    top_up_amount = models.IntegerField(default=100)
    top_up_limit = models.IntegerField(default=10)

    def substract_sms_cost(self, number_of_sms):
        self.balance = self.balance - number_of_sms * settings.COST_OF_SMS
        self.save()

    def save(self, *args, **kwargs):
        from r3sourcer.apps.billing.tasks import charge_for_sms

        super(SMSBalance, self).save(*args, **kwargs)

        if self.balance <= self.top_up_limit:
            charge_for_sms.delay(self.company.id, self.top_up_amount)


class Payment(models.Model):
    PAYMENT_TYPES = Choices(
        ('annual', 'Annual'),
        ('monthly', 'Monthly')
    )
    type = models.CharField(max_length=255, choices=PAYMENT_TYPES)
    created = models.DateTimeField(auto_now_add=True)
    amount = models.IntegerField()
    status = models.CharField(max_length=255)
