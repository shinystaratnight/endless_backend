from django.utils.translation import ugettext_lazy as _
from rest_framework import exceptions

from r3sourcer.apps.core.api.serializers import ApiBaseModelSerializer
from r3sourcer.apps.skills.models import SkillBaseRate, Skill, SkillTag


class SkillBaseRateSerializer(ApiBaseModelSerializer):
    class Meta:
        model = SkillBaseRate
        fields = ('__all__', )


class SkillSerializer(ApiBaseModelSerializer):

    class Meta:
        model = Skill
        fields = (
            'carrier_list_reserve', 'short_name', 'employment_classification', 'active', 'upper_rate_limit',
            'lower_rate_limit', 'default_rate', 'price_list_upper_rate_limit', 'price_list_lower_rate_limit', 'id',
            'price_list_default_rate', {
                'name': ('id', 'name', 'industry')
            }
        )

    def validate(self, validated_data):
        lower_rate = validated_data.get('lower_rate_limit')
        upper_rate = validated_data.get('upper_rate_limit')
        default_rate = validated_data.get('default_rate')

        errors = {}

        if lower_rate and upper_rate and lower_rate > upper_rate:
            errors['lower_rate_limit'] = _('Lower Rate Limit should be lesser than or equal Upper Rate Limit')
        if lower_rate and default_rate and lower_rate > default_rate:
            errors['default_rate'] = _('Default Rate should be greater than or equal Lower Rate Limit')
        if upper_rate and default_rate and default_rate > upper_rate:
            errors['upper_rate_limit'] = _('Upper Rate Limit should be greater than or equal Default Rate')

        lower_rate = validated_data.get('price_list_lower_rate_limit')
        upper_rate = validated_data.get('price_list_upper_rate_limit')
        default_rate = validated_data.get('price_list_default_rate')

        if lower_rate and upper_rate and lower_rate > upper_rate:
            errors['price_list_lower_rate_limit'] = _(
                'Lower Rate Limit should be lesser than or equal Upper Rate Limit'
            )
        if lower_rate and default_rate and lower_rate > default_rate:
            errors['price_list_default_rate'] = _('Default Rate should be greater than or equal Lower Rate Limit')
        if upper_rate and default_rate and default_rate > upper_rate:
            errors['price_list_upper_rate_limit'] = _('Upper Rate Limit should be greater than or equal Default Rate')

        if errors:
            raise exceptions.ValidationError(errors)

        return validated_data


class SkillTagSerializer(ApiBaseModelSerializer):

    class Meta:
        model = SkillTag
        fields = ('id', 'tag', {
            'skill': ('id', 'name')
        })
