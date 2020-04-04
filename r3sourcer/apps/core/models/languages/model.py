from django.db import models
from django.utils.translation import ugettext_lazy as _


class Language(models.Model):
    alpha_2 = models.CharField(max_length=2, primary_key=True)
    name = models.CharField(max_length=64)

    class Meta:
        verbose_name = _("Language")
        verbose_name_plural = _("Languages")

    def __str__(self):
        return self.name
