from django.utils.translation import ugettext_lazy as _
from inflector import Inflector, English
from rest_framework import serializers, exceptions

from r3sourcer.apps.core.api.serializers import ApiBaseModelSerializer
from r3sourcer.apps.core_adapter.utils import api_reverse_lazy
from r3sourcer.apps.pricing import models as pricing_models


class DynamicCoefficientRuleSerializer(ApiBaseModelSerializer):

    method_fields = ('rule', 'rule_endpoint')

    class Meta:
        model = pricing_models.DynamicCoefficientRule
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


class OvertimeRuleSerializer(ApiBaseModelSerializer):

    used = serializers.BooleanField(required=False, label=_('Used for overtime'))

    class Meta:
        model = pricing_models.OvertimeWorkRule
        fields = ('id', 'overtime_hours_from', 'overtime_hours_to', 'used')


class TimeOfDayRuleSerializer(ApiBaseModelSerializer):

    used = serializers.BooleanField(required=False, label=_('Used for Time of The Day'))

    class Meta:
        model = pricing_models.TimeOfDayWorkRule
        fields = ('id', 'time_start', 'time_end', 'used')

    def update(self, obj, validated_data):
        print("validated_data", validated_data)
        return super(TimeOfDayRuleSerializer, self).update(obj, validated_data)


class AllowanceRuleSerializer(ApiBaseModelSerializer):

    used = serializers.BooleanField(required=False, label=_('Is Allowance'))

    class Meta:
        model = pricing_models.AllowanceWorkRule
        fields = ('id', 'allowance_description', 'used')


class WeekdaysRuleSerializer(ApiBaseModelSerializer):

    class Meta:
        model = pricing_models.WeekdayWorkRule
        fields = '__all__'


class RateCoefficientSerializer(ApiBaseModelSerializer):

    method_fields = ('rules', )

    overtime = OvertimeRuleSerializer(required=False)
    weekdays = WeekdaysRuleSerializer(required=False)
    timeofday = TimeOfDayRuleSerializer(required=False, read_only=False)
    allowance = AllowanceRuleSerializer(required=False)

    class Meta:
        model = pricing_models.RateCoefficient
        fields = ('id', 'industry', 'name', 'active', 'group', 'overtime', 'weekdays', 'timeofday', 'allowance')

    def get_rules(self, obj):
        if obj is None:
            return []

        return [rule['rule'] for rule in DynamicCoefficientRuleSerializer(
            obj.rate_coefficient_rules.order_by('-priority'),
            many=True, fields=['priority', 'rule', 'rule_endpoint']
        ).data]

    def _get_rule_objects(self, validated_data, obj=None):
        rules = []
        for field_name, field in self.fields.items():
            if not isinstance(field, ApiBaseModelSerializer):
                continue

            model = field.Meta.model
            data = validated_data.pop(field_name, None)

            # TODO check if used is False - delete object
            # used = data.pop('used', False)
            if isinstance(field, WeekdaysRuleSerializer):
                save = any(data.values())
            else:
                save = data

            if save:
                if obj:
                    rule_obj, created = model.objects.update_or_create(
                        id=data.get('id'),
                        defaults=data
                    )

                    setattr(obj, field_name, rule_obj)

                    if created:
                        pricing_models.DynamicCoefficientRule.objects.create(
                            rate_coefficient=obj, rule=rule_obj
                        )
                else:
                    rule_obj = model.objects.create(**data)

                rules.append(rule_obj)

        return rules

    def create(self, validated_data):
        rules = self._get_rule_objects(validated_data)

        obj = super(RateCoefficientSerializer, self).create(validated_data)

        for rule_obj in rules:
            pricing_models.DynamicCoefficientRule.objects.create(
                rate_coefficient=obj, rule=rule_obj
            )

        return obj

    def update(self, obj, validated_data):
        self._get_rule_objects(validated_data, obj)

        return super(RateCoefficientSerializer, self).update(obj, validated_data)


class IndustrySerializer(ApiBaseModelSerializer):

    class Meta:
        model = pricing_models.Industry
        fields = ('__all__',)


class PriceListRateSerializer(ApiBaseModelSerializer):

    class Meta:
        model = pricing_models.PriceListRate
        fields = ('__all__',)

    def validate(self, data):
        skill = data.get('skill')

        is_lower = skill.price_list_lower_rate_limit and data.get('hourly_rate') < skill.price_list_lower_rate_limit
        is_upper = skill.price_list_upper_rate_limit and data.get('hourly_rate') > skill.price_list_upper_rate_limit
        if is_lower or is_upper:
            raise exceptions.ValidationError({
                'hourly_rate': _('Hourly rate should be between {lower_limit} and {upper_limit}').format(
                    lower_limit=skill.price_list_lower_rate_limit, upper_limit=skill.price_list_upper_rate_limit,
                )
            })

        return data
