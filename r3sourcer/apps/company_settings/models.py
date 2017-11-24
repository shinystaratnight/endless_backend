from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
from django.db import models


class GlobalPermissionManager(models.Manager):
    def get_queryset(self):
        return super(GlobalPermissionManager, self).get_queryset().filter(content_type__model='global_permission')


class GlobalPermission(Permission):
    """A global permission, not attached to a model"""

    CONTENT_TYPE = 'global_permission'
    objects = GlobalPermissionManager()

    class Meta:
        proxy = True

    def save(self, *args, **kwargs):
        content_type, _ = ContentType.objects.get_or_create(model=self.CONTENT_TYPE, app_label=self._meta.app_label)
        self.content_type = content_type
        super(GlobalPermission, self).save(*args, **kwargs)
