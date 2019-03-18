from django.contrib.contenttypes.models import ContentType

from rest_framework import status
from rest_framework.response import Response

from r3sourcer.apps.core.api import viewsets as core_viewsets
from r3sourcer.apps.core.utils.companies import get_site_master_company
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

    def perform_create(self, serializer):
        instance = serializer.save()

        master_company = get_site_master_company(request=self.request)
        pricing_models.RateCoefficientRel.objects.create(
            rate_coefficient=instance,
            company=master_company
        )

    def destroy(self, request, *args, **kwargs):
        return Response({'error': 'Unable to delete due relation to calculation'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)
