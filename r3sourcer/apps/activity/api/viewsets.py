from r3sourcer.apps.core.api.viewsets import BaseApiViewset

from .. import models


class ActivityViewset(BaseApiViewset):
    def get_queryset(self):
        if self.request.user.is_superuser:
            return models.Activity.objects.all()

        return models.Activity.objects.filter(
            contact__user_id=self.request.user.id
        )
