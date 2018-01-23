from django.contrib.contenttypes.models import ContentType

from r3sourcer.apps.core.api import viewsets as core_viewsets
from r3sourcer.apps.pricing import models as pricing_models


class RateCoefficientViewset(core_viewsets.BaseApiViewset):

    exclude_empty = True

    def get_object(self):
        obj = super().get_object()

        if self.request.method == 'POST':
            return obj

        extra_map = {
            'overtime': pricing_models.OvertimeWorkRule,
            'weekdays': pricing_models.WeekdayWorkRule,
            'timeofday': pricing_models.TimeOfDayWorkRule,
            'allowance': pricing_models.AllowanceWorkRule,
        }

        for extra, extra_class in extra_map.items():
            extra_obj = obj.rate_coefficient_rules.filter(
                rule_type=ContentType.objects.get_for_model(extra_class)
            ).first()
            rule = extra_obj and extra_obj.rule
            if rule:
                setattr(rule, 'used', rule is not None)
            setattr(obj, extra, rule)

        return obj
