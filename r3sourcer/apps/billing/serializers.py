from rest_framework import serializers

from r3sourcer.apps.billing.models import Subscription, Payment, Discount
from r3sourcer.apps.core.models.core import Company


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ('company', 'name', 'type', 'price', 'worker_count', 'created', 'active', 'id', 'current_period_start',
                  'current_period_end', 'last_time_billed')


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ('type', 'created', 'amount', 'status', 'invoice_url')


class CompanySerializer(serializers.ModelSerializer):
    subscription = serializers.SerializerMethodField()
    sms_balance = serializers.IntegerField(source='sms_balance.balance')

    class Meta:
        model = Company
        fields = ('name', 'short_name', 'subscription', 'sms_balance')

    def get_subscription(self, company):
        subscription = company.subscriptions.filter(active=True).first()
        serializer = SubscriptionSerializer(instance=subscription)
        return serializer.data


class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = ('company', 'payment_type', 'percent_off', 'amount_off', 'active', 'duration', 'duration_in_months')
