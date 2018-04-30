from rest_framework import serializers

from r3sourcer.apps.billing.models import Plan


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ('company', 'name', 'type', 'price', 'worker_count', 'created', 'active', 'id')
