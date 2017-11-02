from django.db import models


class SelectRelatedSkillManager(models.Manager):
    def get_queryset(self):
        return super(SelectRelatedSkillManager, self).get_queryset().select_related('skill')
