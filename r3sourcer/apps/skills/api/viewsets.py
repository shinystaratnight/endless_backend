from r3sourcer.apps.core.api import viewsets as core_viewsets
from r3sourcer.apps.skills.models import Skill


class SkillNameViewSet(core_viewsets.BaseApiViewset):
    def _filter_list(self):
        if not hasattr(self, '_map_skill'):
            map_skill = dict()
            for skill in Skill.objects.filter(name__industry__in=self.request.user.company.industries.all(),
                                              company=self.request.user.company).select_related('name'):
                map_skill.update({skill.name.name: skill})
            self._map_skill = map_skill

        return self._map_skill
