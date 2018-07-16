from rest_framework import serializers

from r3sourcer.apps.billing.models import Subscription, Payment


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ('company', 'name', 'type', 'price', 'worker_count', 'created', 'active', 'id', 'current_period_start',
                  'current_period_end')


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ('type', 'created', 'amount', 'status')
