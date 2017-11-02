from inflector import Inflector, English

from r3sourcer.apps.core.api.serializers import ApiBaseModelSerializer
from r3sourcer.apps.core_adapter.utils import api_reverse_lazy
from .. import models


class DynamicCoefficientRuleSerializer(ApiBaseModelSerializer):

    method_fields = ('rule', 'rule_endpoint')

    class Meta:
        model = models.DynamicCoefficientRule
        fields = ('rate_coefficient', 'priority', 'id')

    def get_rule(self, obj):
        if obj is None:
            return

        return str(obj.rule)

    def get_rule_endpoint(self, obj):
        if obj is None:
            return

        endpoint = '%s/%s' % (
            obj.rule_type.app_label.replace('_', '-'),
            Inflector(English).pluralize(obj.rule_type.model)
        )
        return api_reverse_lazy(endpoint, 'detail', pk=str(obj.rule_id))


class RateCoefficientSerializer(ApiBaseModelSerializer):

    method_fields = ('rules', )

    class Meta:
        model = models.RateCoefficient
        fields = '__all__'

    def get_rules(self, obj):
        if obj is None:
            return []

        return DynamicCoefficientRuleSerializer(
            obj.rate_coefficient_rules.order_by('-priority'),
            many=True, fields=['priority', 'rule', 'rule_endpoint']
        ).data
