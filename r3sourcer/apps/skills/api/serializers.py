from r3sourcer.apps.core.api.serializers import ApiBaseModelSerializer
from r3sourcer.apps.pricing.api.serializers import PriceListRateSerializer
from r3sourcer.apps.skills.models import SkillBaseRate, Skill


class SkillBaseRateSerializer(ApiBaseModelSerializer):
    class Meta:
        model = SkillBaseRate
        fields = '__all__'


class SkillSerializer(ApiBaseModelSerializer):

    skill_rate_defaults = SkillBaseRateSerializer(many=True)
    price_list_rates = PriceListRateSerializer(many=True)

    many_related_fields = {
        'skill_rate_defaults': 'skill',
        'price_list_rates': 'skill',
    }

    class Meta:
        model = Skill
        fields = (
            '__all__',
            {
                'skill_rate_defaults': ('id', 'hourly_rate', 'default_rate'),
                'price_list_rates': ('id',)
            },
        )
