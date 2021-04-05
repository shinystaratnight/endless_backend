import datetime
import logging
from decimal import Decimal
import pytz
import stripe
from django.conf import settings
from django.db import models
from django.utils.formats import date_format
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices
from stripe.error import InvalidRequestError

from r3sourcer import ref
from r3sourcer.apps.core import tasks
from r3sourcer.apps.core.models.mixins import CompanyTimeZoneMixin
from r3sourcer.apps.email_interface.models import EmailTemplate, DefaultEmailTemplate
from r3sourcer.helpers.datetimes import utc_now

logger = logging.getLogger(__name__)

class Subscription(CompanyTimeZoneMixin):
    ALLOWED_STATUSES = ('active', 'incomplete', 'trialing')
    SUBSCRIPTION_STATUSES = Choices(
        ('active', 'Active'),
        ('past_due', 'Past due'),
        ('canceled', 'Canceled'),
        ('unpaid', 'Unpaid'),
    )
    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        related_name='subscriptions')
    name = models.CharField(max_length=255)
    subscription_type = models.ForeignKey(
        'billing.SubscriptionType',
        on_delete=models.DO_NOTHING,
        related_name='subscriptions')
    price = models.PositiveIntegerField()
    worker_count = models.PositiveIntegerField()
    created = ref.DTField()
    active = models.BooleanField(default=True)
    status = models.CharField(max_length=255, choices=SUBSCRIPTION_STATUSES)
    current_period_start = ref.DTField(blank=True, null=True)
    current_period_end = ref.DTField(blank=True, null=True)

    # stripe ids
    plan_id = models.CharField(max_length=255)
    subscription_id = models.CharField(max_length=255)

    @property
    def created_tz(self):
        return self.utc2local(self.created)

    @property
    def created_utc(self):
        return self.created

    @property
    def current_period_start_tz(self):
        return self.utc2local(self.current_period_start)

    @property
    def current_period_start_utc(self):
        return self.current_period_start

    @property
    def current_period_end_tz(self):
        return self.utc2local(self.current_period_end)

    @property
    def current_period_end_utc(self):
        return self.current_period_end

    def __str__(self):
        return "{} with {} workers. Status: {}".format(self.company.name, self.worker_count, self.status)

    def get_total_subscription_amount(self):
        active_workers = self.company.active_workers(self.current_period_start)
        if self.subscription_type.type == self.subscription_type.SUBSCRIPTION_TYPES.monthly:
            total_amount = self.subscription_type.start_range_price_monthly
        else:
            total_amount = self.subscription_type.start_range_price_annual
        start_workers = settings.SUBSCRIPTION_START_WORKERS
        if active_workers > start_workers:
            total_amount += (active_workers - start_workers) * self.subscription_type.step_change_val
        if self.subscription_type.type == self.subscription_type.SUBSCRIPTION_TYPES.annual:
            if self.subscription_type.percentage_discount:
                total_amount = (total_amount * 12) - (total_amount * 12 / 100 * self.subscription_type.percentage_discount)
            else:
                total_amount = total_amount * 12 * settings.SUBSCRIPTION_DEFAULT_DISCOUNT
        if self.subscription_type.type == self.subscription_type.SUBSCRIPTION_TYPES.monthly:
            if self.subscription_type.percentage_discount:
                total_amount = total_amount - (total_amount / 100 * self.subscription_type.percentage_discount)
            else:
                total_amount = total_amount
        return total_amount

    def sync_status(self):
        stripe.api_key = StripeCountryAccount.get_stripe_key_on_company(self.company)
        subscription = stripe.Subscription.retrieve(self.subscription_id)
        self.status = subscription.status
        if subscription.status not in self.ALLOWED_STATUSES:
            self.active = False
        else:
            self.active = True

    def update_permissions_on_status(self):
        this_user = self.company.get_user()
        if this_user.trial_period_start:
            end_of_trial = this_user.trial_period_start + datetime.timedelta(days=30)
            if self.status not in self.ALLOWED_STATUSES and self.now_utc > end_of_trial:
                self.deactivate(user_id=(str(this_user.id)))
        # elif self.status in allowed_statuses:
        #     self.activate(user_id=(str(this_user.id)))

    def sync_periods(self):
        stripe.api_key = StripeCountryAccount.get_stripe_key_on_company(self.company)
        subscription = stripe.Subscription.retrieve(self.subscription_id)
        self.current_period_start = datetime.datetime.utcfromtimestamp(subscription.current_period_start)
        self.current_period_end = datetime.datetime.utcfromtimestamp(subscription.current_period_end)
        if self.current_period_end.replace(tzinfo=pytz.UTC) <= self.now_utc and self.company.get_user():
            self.deactivate(user_id=(str(self.company.get_user().id)))

    def deactivate(self, user_id=None):
        stripe.api_key = StripeCountryAccount.get_stripe_key_on_company(self.company)
        sub = stripe.Subscription.retrieve(self.subscription_id)
        try:
            sub.modify(self.subscription_id, cancel_at_period_end=True, prorate=False)
        except InvalidRequestError as e:
            logger.warning('Subscription is missed, probably cancelled: {}'.format(e.message))
        if user_id:
            tasks.cancel_subscription_access.apply_async([user_id])

    @staticmethod
    def activate(user_id=None):
        if user_id:
            tasks.give_subscription_access.apply_async([user_id])

    @property
    def last_time_billed(self):
        last_payment = self.company.payment_set.order_by('-created').first()

        if last_payment:
            return last_payment.created

    @property
    def sms_balance(self):
        return self.company.sms_balance.balance

    def save(self, *args, **kwargs):
        if not self.created:
            self.created = self.now_utc
        super().save(*args, **kwargs)

        if self.active:
            subscriptions = Subscription.objects.filter(
                company=self.company,
                active=True,
            ).exclude(id=self.id)

            for subscription in subscriptions:
                subscription.deactivate()
                subscription.active = False
                subscription.save()


class SMSBalance(models.Model):
    company = models.OneToOneField(
        'core.Company',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='sms_balance')
    balance = models.DecimalField(default=0, max_digits=8, decimal_places=2)
    top_up_amount = models.IntegerField(default=100)
    top_up_limit = models.IntegerField(default=10)
    last_payment = models.ForeignKey('Payment', blank=True, null=True)
    cost_of_segment = models.DecimalField(default=0, max_digits=8, decimal_places=2)
    auto_charge = models.BooleanField(default=False, verbose_name=_('Auto Charge'))
    low_balance_sent = models.BooleanField(default=False)
    ran_out_balance_sent = models.BooleanField(default=False)

    @property
    def segment_cost(self):
        return self.cost_of_segment or settings.COST_OF_SMS_SEGMENT

    def substract_sms_cost(self, number_of_segments):
        amount = Decimal(number_of_segments) * self.segment_cost
        self.balance = self.balance - Decimal(amount)
        self.save()

    def save(self, *args, **kwargs):
        from r3sourcer.apps.billing.tasks import charge_for_sms

        if self.balance <= self.top_up_limit and self.auto_charge is True:
            charge_for_sms.delay(self.company.id, self.top_up_amount, self.id)

        if self.company.is_master:
            low_limit = SMSBalanceLimits.objects.filter(name="Low").first()
            if low_limit:
                if Decimal(self.balance) < low_limit.low_balance_limit and self.low_balance_sent is False:
                    tasks.send_sms_balance_is_low_email.delay(self.company.id, template=low_limit.email_template.slug)
                    self.low_balance_sent = True

                if Decimal(self.balance) > low_limit.low_balance_limit and self.low_balance_sent is True:
                    self.low_balance_sent = False

            ran_out_limit = SMSBalanceLimits.objects.filter(name="Ran out").first()
            if ran_out_limit:
                if Decimal(self.balance) < ran_out_limit.low_balance_limit and self.ran_out_balance_sent is False:
                    tasks.send_sms_balance_ran_out_email.delay(self.company.id, template=ran_out_limit.email_template.slug)
                    self.ran_out_balance_sent = True

                if Decimal(self.balance) > ran_out_limit.low_balance_limit and self.ran_out_balance_sent is True:
                    self.ran_out_balance_sent = False

        if Decimal(self.balance) - self.segment_cost < 0:
            self.company.sms_enabled = False
            self.company.save()

        if not self.company.sms_enabled and Decimal(self.balance) - self.segment_cost > 0:
            self.company.sms_enabled = True
            self.company.save()

        super().save(*args, **kwargs)


class Payment(CompanyTimeZoneMixin):
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
    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE)
    type = models.CharField(max_length=255, choices=PAYMENT_TYPES)
    created = ref.DTField()
    amount = models.IntegerField()
    status = models.CharField(max_length=255, choices=PAYMENT_STATUSES, default=PAYMENT_STATUSES.not_paid)
    stripe_id = models.CharField(max_length=255)
    invoice_url = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return '{} Payment at {}'.format(self.company, date_format(self.created, settings.DATETIME_MYOB_FORMAT))

    @property
    def created_tz(self):
        return self.utc2local(self.created)

    @property
    def created_utc(self):
        return self.created

    def save(self, *args, **kwargs):
        if not self.created:
            self.created = self.now_utc
        super().save(*args, **kwargs)


class Discount(CompanyTimeZoneMixin):
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
    company = models.ForeignKey(
        'core.Company',
        related_name='discounts')
    payment_type = models.CharField(max_length=255, choices=PAYMENT_TYPES, blank=True, null=True)
    percent_off = models.IntegerField(blank=True, null=True)
    amount_off = models.IntegerField(blank=True, null=True)
    active = models.BooleanField(default=True)
    duration = models.CharField(max_length=255, choices=DURATIONS)
    duration_in_months = models.IntegerField(blank=True, null=True)
    created = ref.DTField()

    @property
    def created_tz(self):
        return self.utc2local(self.created)

    @property
    def created_utc(self):
        return self.created

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

            if self.created + datetime.timedelta(days=duration_in_days) < utc_now():
                self.active = False
                self.save()

        return discounted_value

    def save(self, *args, **kwargs):
        if not self.created:
            self.created = self.now_utc

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
            StripeCountryAccount.get_stripe_key_on_company(self.company)
            coupon = stripe.Coupon.create(**coupon_data)
            subscription = stripe.Subscription.retrieve(subscription.subscription_id)
            subscription.coupon = coupon.id
            subscription.save()
        super().save(*args, **kwargs)


class SubscriptionType(models.Model):
    SUBSCRIPTION_TYPES = Choices(
        ('annual', 'Annual'),
        ('monthly', 'Monthly')
    )
    type = models.CharField(max_length=255, choices=SUBSCRIPTION_TYPES)
    employess_total_num = models.PositiveIntegerField(blank=True, null=True)
    max_employess_num = models.PositiveIntegerField(blank=True, null=True)
    start_range = models.PositiveIntegerField(blank=True, null=True)
    start_range_price_monthly = models.PositiveIntegerField(blank=True, null=True)
    start_range_price_annual = models.PositiveIntegerField(blank=True, null=True)
    step_change_val = models.PositiveIntegerField(blank=True, null=True)
    heading = models.CharField(max_length=255, blank=True, null=True)
    amount = models.PositiveIntegerField(blank=True, null=True)
    amount_tag_line = models.CharField(max_length=255, blank=True, null=True)
    amount_annual = models.CharField(max_length=255, blank=True, null=True)
    table_text = models.CharField(max_length=255, blank=True, null=True)
    discount_comment = models.CharField(max_length=255, blank=True, null=True)
    percentage_discount = models.PositiveIntegerField(blank=True, null=True)
    amount_comment = models.CharField(max_length=255, blank=True, null=True)
    heading_tag_line = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.type

    def save(self, *args, **kwargs):
        from r3sourcer.apps.billing.tasks import charge_for_new_amount
        charge_for_new_amount.delay()
        super().save(*args, **kwargs)


class StripeCountryAccount(models.Model):
    country = models.ForeignKey(
        'core.Country',
        to_field='code2',
        null=True,
        blank=True,
    )
    stripe_public_key = models.CharField(max_length=255, blank=True, null=True)
    stripe_secret_key = models.CharField(max_length=255, blank=True, null=True)
    stripe_product_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = _("Stripe Country Account")
        verbose_name_plural = _("Stripe Country Accounts")

    def __str__(self):
        return self.country.name

    @classmethod
    def get_stripe_key(cls, country_code2='EE'):
        """
        return: settings api key for Stripe Country Account
        default: EE for Estonia Stripe Account
        """
        if settings.TEST:
            return settings.STRIPE_SECRET_API_KEY
        stripe_accounts = cls.objects.filter(country=country_code2)
        if not stripe_accounts and country_code2 == 'EE':
            raise Exception("Not Even Estonia account found. Configure stripe accounts!")
        stripe_account = stripe_accounts.first() or cls.objects.filter(country='EE').first()
        api_key = stripe_account.stripe_secret_key
        return api_key

    @classmethod
    def get_stripe_key_on_company(cls, company):
        country_code = company.get_country_code()
        api_key = cls.get_stripe_key(country_code)
        return api_key

    @classmethod
    def get_stripe_pub(cls, country_code2='EE'):
        if settings.TEST:
            return settings.STRIPE_PUBLIC_API_KEY
        stripe_accounts = cls.objects.filter(country=country_code2)
        if not stripe_accounts and country_code2 == 'EE':
            raise Exception("Not Even Estonia account found. Configure stripe accounts!")
        stripe_account = stripe_accounts.first() or cls.objects.filter(country='EE').first()
        api_key = stripe_account.stripe_public_key
        return api_key


class SMSBalanceLimits(models.Model):
    name = models.CharField(max_length=255, unique=True)
    low_balance_limit = models.PositiveIntegerField(default=20)
    email_template = models.ForeignKey(DefaultEmailTemplate)
