from django.utils.translation import ugettext_lazy as _
from rest_framework import exceptions, serializers

from r3sourcer.apps.core.api.serializers import ApiBaseModelSerializer
from r3sourcer.apps.skills.models import SkillBaseRate, Skill, SkillTag, SkillName, SkillRateRange, WorkType


class SkillBaseRateSerializer(ApiBaseModelSerializer):
    class Meta:
        model = SkillBaseRate
        fields = ('__all__', )


class SkillSerializer(ApiBaseModelSerializer):

    class Meta:
        model = Skill
        fields = (
            'id', 'company', 'carrier_list_reserve', 'short_name', 'employment_classification', 'active',
            {'name': ('id', 'name', {'translations': ('language', 'value')},
                         {'industry': ('id', 'type', {'translations': ('language', 'value')})})
            },
            {'skill_rate_ranges': ('id','uom', 'worktype',
                                   'upper_rate_limit', 'lower_rate_limit', 'default_rate',
                                   'price_list_upper_rate_limit', 'price_list_lower_rate_limit',
                                   'price_list_default_rate'),
            },
        )


class SkillTagSerializer(ApiBaseModelSerializer):

    class Meta:
        model = SkillTag
        fields = (
            'id',
            {'tag': ('name', {'translations': ('language', 'value')})},
            {'skill': ('id', {'name': ('name', {'translations': ('language', 'value')})})},
        )


class SkillNameSerializer(ApiBaseModelSerializer):

    method_fields = ('active', 'skill_id', 'carrier_list_reserve')

    class Meta:
        model = SkillName
        fields = (
            'id',
            {'name': ('name', {'translations': ('language', 'value')})},
            {'industry': ('id', 'type', {'translations': ('language', 'value')}),
             'translations': ('language', 'value'),
            #  'work_types': ('id', 'name', {'translations': ('language', 'value')}),
            },
        )

    def get_active(self, obj):
        try:
            return self.context['view']._filter_list()[obj.name].active
        except KeyError:
            return False

    def get_skill_id(self, obj):
        try:
            return self.context['view']._filter_list()[obj.name].id
        except KeyError:
            return None

    def get_carrier_list_reserve(self, obj):
        try:
            return self.context['view']._filter_list()[obj.name].carrier_list_reserve
        except KeyError:
            return None


class SkillRateRangeSerializer(ApiBaseModelSerializer):

    class Meta:
        model = SkillRateRange
        fields = (
            'id', 'skill', 'worktype', 'uom',
            'upper_rate_limit', 'lower_rate_limit', 'default_rate',
            'price_list_upper_rate_limit', 'price_list_lower_rate_limit', 'price_list_default_rate'
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


class WorkTypeSerializer(ApiBaseModelSerializer):

    class Meta:
        model = WorkType
        fields = (
            'id', 'skill_name', 'name',
            {'translations': ('language', 'value')},
            )
