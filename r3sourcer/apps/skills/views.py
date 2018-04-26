from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from r3sourcer.apps.skills.models import SkillBaseRate


class MakeSkillBaseRateDefaultView(APIView):
    def post(self, *args, **kwargs):
        rate = get_object_or_404(SkillBaseRate, id=self.kwargs['id'])
        SkillBaseRate.objects.all().update(default_rate=False)
        rate.default_rate = True
        rate.save()
        return Response()
