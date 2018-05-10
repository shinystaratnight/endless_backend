from rest_framework import serializers

from r3sourcer.apps.billing.models import Subscription


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ('company', 'name', 'type', 'price', 'worker_count', 'created', 'active', 'id')
