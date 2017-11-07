from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .core import UUIDModel


__all__ = [
    'DashboardModule',
    'UserDashboardModule'
]


class DashboardModule(UUIDModel):

    content_type = models.OneToOneField(
        'contenttypes.ContentType',
        verbose_name=_("Model"),
        unique=True,
        related_name='+'
    )

    is_active = models.BooleanField(
        _("Is active"),
        default=True
    )

    def __str__(self):
        return str(self.content_type)

    class Meta:
        verbose_name = _("Dashboard module")
        verbose_name_plural = _("Dashboard modules")
        permissions = (
            ('can_use_module', _("Can use this module")),
        )


class UserDashboardModule(UUIDModel):

    company_contact = models.ForeignKey(
        'core.CompanyContact',
        verbose_name=_("Company contact"),
        related_name='dashboard_modules'
    )

    dashboard_module = models.ForeignKey(
        'DashboardModule',
        verbose_name=_("Dashboard module"),
        related_name='dashboard_modules'
    )

    position = models.PositiveIntegerField(
        verbose_name=_("position"),
        help_text=_("would be used for ordering")
    )

    ui_config = JSONField(
        verbose_name=_("UI config"),
        default={},
        blank=True
    )

    def __str__(self):
        return '{company_contact}: {module}'.format(
            company_contact=self.company_contact,
            module=self.dashboard_module,
        )

    def is_available(self):
        return self.dashboard_module.is_active

    class Meta:
        ordering = ['company_contact', '-position']
        unique_together = ('company_contact', 'dashboard_module')
        verbose_name = _("User dashboard module")
        verbose_name_plural = _("User dashboard modules")
