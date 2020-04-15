from django.db import models
from django.utils.translation import ugettext_lazy as _


class BankAccountLayout(models.Model):
    name = models.CharField(max_length=64)
    slug = models.SlugField(max_length=32, unique=True)
    description = models.CharField(max_length=128)

    class Meta:
        verbose_name = _("Bank account layout")
        verbose_name_plural = _("Bank account layouts")

    def __str__(self):
        return self.name
