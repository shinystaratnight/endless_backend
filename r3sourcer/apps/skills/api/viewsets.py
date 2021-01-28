from r3sourcer.apps.core.api import viewsets as core_viewsets
from r3sourcer.apps.skills.models import Skill


class SkillNameViewSet(core_viewsets.BaseApiViewset):

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(
            industry__in=self.request.user.company.industries.all(),
            skills__company=self.request.user.company,
        )
        if self.request.query_params.get('ordering'):
            ordering = self.request.query_params.get('ordering')
            qs = qs.order_by(*ordering.split(','))
        else:
            qs = qs.order_by('name')

        return qs

    def _filter_list(self):
        if not hasattr(self, '_map_skill'):
            map_skill = dict()
            for skill in Skill.objects.filter(name__industry__in=self.request.user.company.industries.all(),
                                              company=self.request.user.company).select_related('name'):
                map_skill.update({skill.name.name: skill})
            self._map_skill = map_skill

        return self._map_skill


class WorkTypeViewSet(core_viewsets.BaseApiViewset):

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(
            skill_name__industry__in=self.request.user.company.industries.all(),
        )
        if self.request.query_params.get('ordering'):
            ordering = self.request.query_params.get('ordering')
            qs = qs.order_by(*ordering.split(','))
        else:
            qs = qs.order_by('skill_name')

        return qs


class SkillRateRangeViewSet(core_viewsets.BaseApiViewset):

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(
            skill__name__industry__in=self.request.user.company.industries.all(),
        )
        if self.request.query_params.get('ordering'):
            ordering = self.request.query_params.get('ordering')
            qs = qs.order_by(*ordering.split(','))
        else:
            qs = qs.order_by('skill')

        return qs
