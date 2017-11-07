from django.db import models
from django.utils.translation import ugettext_lazy as _
from r3sourcer.apps.core.models import UUIDModel

from .managers import SelectRelatedSkillManager


class EmploymentClassification(UUIDModel):

    name = models.CharField(
        max_length=255,
        verbose_name=_('Name')
    )

    class Meta:
        verbose_name = _("Employment Classification")
        verbose_name_plural = _("Employment Classifications")

    def __str__(self):
        return self.name


class Skill(UUIDModel):

    name = models.CharField(max_length=63, verbose_name=_("Skill Name"))

    carrier_list_reserve = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_('Carrier List Reserve')
    )

    short_name = models.CharField(
        max_length=15,
        verbose_name=_("Short Name"),
        help_text=_("Abbreviation, for use by staff reports and dashboards"),
        blank=True
    )

    employment_classification = models.ForeignKey(
        EmploymentClassification,
        on_delete=models.PROTECT,
        related_name="skills",
        verbose_name=_("Employment Classification"),
        null=True,
        blank=True
    )
    active = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        verbose_name = _("Skill")
        verbose_name_plural = _("Skills")

    def __str__(self):
        return self.name


class SkillBaseRate(UUIDModel):

    skill = models.ForeignKey(
        Skill,
        on_delete=models.PROTECT,
        related_name="skill_rate_defaults",
        verbose_name=_("Skill")
    )

    hourly_rate = models.DecimalField(
        decimal_places=2,
        max_digits=8,
        verbose_name=_("Hourly Rate"),
        default=0.00
    )

    objects = SelectRelatedSkillManager()

    class Meta:
        verbose_name = _("Skill Base Rate")
        verbose_name_plural = _("Skill Base Rates")
        ordering = ('hourly_rate',)

    def __str__(self):
        return '{} ${}/h'.format(str(self.skill), str(self.hourly_rate))
