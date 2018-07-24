from r3sourcer.apps.core.api.serializers import ApiBaseModelSerializer
from r3sourcer.apps.skills.models import SkillBaseRate, Skill


class SkillBaseRateSerializer(ApiBaseModelSerializer):
    class Meta:
        model = SkillBaseRate
        fields = ('__all__', )


class SkillSerializer(ApiBaseModelSerializer):

    class Meta:
        model = Skill
        fields = (
            'name', 'carrier_list_reserve', 'short_name', 'employment_classification', 'active', 'upper_rate_limit',
            'lower_rate_limit', 'default_rate', 'price_list_upper_rate_limit', 'price_list_lower_rate_limit', 'id',
            'price_list_default_rate',
        )
