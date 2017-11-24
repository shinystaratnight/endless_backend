from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

from r3sourcer.apps.core.models import UUIDModel
from r3sourcer.apps.skills.managers import SelectRelatedSkillManager


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

    def clean(self, *args, **kwargs):
        have_default_base_rate = self.skill_rate_defaults.filter(default_rate=True).count()
        have_default_price_list_rate = self.price_list_rates.filter(default_rate=True).count()

        if self.active and (not have_default_base_rate or not have_default_price_list_rate):
            raise ValidationError("Skill cant be active it doesnt have default price list rate and defalut base rate.")

        super(Skill, self).clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.full_clean()
        super(Skill, self).save(*args, **kwargs)

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

    default_rate = models.BooleanField(
        default=False,
        verbose_name=_("Is Default Rate")
    )

    objects = SelectRelatedSkillManager()

    class Meta:
        verbose_name = _("Skill Base Rate")
        verbose_name_plural = _("Skill Base Rates")
        ordering = ('hourly_rate',)
        unique_together = ('skill', 'hourly_rate')

    @classmethod
    def set_default_rate(cls, sender, instance, created, **kwargs):
        if created and not instance.skill.skill_rate_defaults.exclude(pk=instance.pk).count():
            instance.default_rate = True
            instance.save()

    def clean(self, *args, **kwargs):
        if self.default_rate:
            default_rates = self.skill.skill_rate_defaults.filter(default_rate=True) \
                                                          .exclude(pk=self.pk)
            if default_rates.count():
                raise ValidationError('Only one rate for the skill can be set to "True"')

        super(SkillBaseRate, self).clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.full_clean()
        super(SkillBaseRate, self).save(*args, **kwargs)

    def __str__(self):
        return '{} ${}/h'.format(str(self.skill), str(self.hourly_rate))


post_save.connect(SkillBaseRate.set_default_rate, sender=SkillBaseRate)
