from r3sourcer.apps.core.api.serializers import ApiBaseModelSerializer
from r3sourcer.apps.skills.models import SkillBaseRate, Skill


class SkillBaseRateSerializer(ApiBaseModelSerializer):
    class Meta:
        model = SkillBaseRate
        fields = ('__all__', )


class SkillSerializer(ApiBaseModelSerializer):

    method_fields = ('default_rate', )

    class Meta:
        model = Skill
        fields = ('__all__',)

    def get_default_rate(self, obj):
        default_rate = obj.skill_rate_defaults.filter(default_rate=True).first()
        if not default_rate:
            default_rate = obj.skill_rate_defaults.filter(hourly_rate__gt=0.0).order_by('hourly_rate').first()

        return default_rate.hourly_rate if default_rate else 0.0
