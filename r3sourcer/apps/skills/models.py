from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

from r3sourcer.apps.core.mixins import MYOBMixin
from r3sourcer.apps.core.models import UUIDModel, Tag
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

    @classmethod
    def is_owned(cls):
        return False


class Skill(MYOBMixin, UUIDModel):

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

    upper_rate_limit = models.DecimalField(
        decimal_places=2,
        max_digits=16,
        blank=True,
        null=True
    )

    lower_rate_limit = models.DecimalField(
        decimal_places=2,
        max_digits=16,
        blank=True,
        null=True
    )

    default_rate = models.DecimalField(
        decimal_places=2,
        max_digits=16,
        blank=True,
        null=True
    )

    price_list_upper_rate_limit = models.DecimalField(
        decimal_places=2,
        max_digits=16,
        blank=True,
        null=True
    )

    price_list_lower_rate_limit = models.DecimalField(
        decimal_places=2,
        max_digits=16,
        blank=True,
        null=True
    )

    price_list_default_rate = models.DecimalField(
        decimal_places=2,
        max_digits=16,
        blank=True,
        null=True
    )

    tags = models.ManyToManyField(
        Tag,
        related_name='skills',
        through='SkillTag'
    )

    class Meta:
        verbose_name = _("Skill")
        verbose_name_plural = _("Skills")

    def clean(self, *args, **kwargs):
        have_default_base_rate = self.default_rate
        have_default_price_list_rate = self.price_list_default_rate

        if self.active:
            if not have_default_base_rate and not have_default_price_list_rate:
                raise ValidationError(
                    "Skill cant be active. It doesnt have default price list rate and defalut base rate."
                )
            elif not have_default_base_rate:
                raise ValidationError("Skill cant be active. It doesnt have default base rate.")
            elif not have_default_price_list_rate:
                raise ValidationError("Skill cant be active. It doesnt have default price list rate.")

        super(Skill, self).clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.full_clean()
        super(Skill, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_myob_name(self):
        name = self.short_name
        if not name:
            parts = self.name.split(' ')
            parts_len = len(parts)
            trim_size = 1

            if parts_len == 1:
                trim_size = 6
            elif parts_len == 2 or parts_len == 3:
                trim_size = 6 // parts_len

            name = ''.join([p[:trim_size] for p in parts])

        return name[:6]

    @classmethod
    def is_owned(cls):
        return False


class SkillBaseRate(UUIDModel):

    skill = models.ForeignKey(
        Skill,
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

    def save(self, *args, **kwargs):
        super(SkillBaseRate, self).save(*args, **kwargs)

        if self.default_rate:
            default_rates = self.skill.skill_rate_defaults.filter(default_rate=True) \
                                                          .exclude(pk=self.pk)
            if default_rates:
                default_rates.update(default_rate=False)

    def __str__(self):
        return '{} ${}/h'.format(str(self.skill), str(self.hourly_rate))


post_save.connect(SkillBaseRate.set_default_rate, sender=SkillBaseRate)


class SkillTag(UUIDModel):
    tag = models.ForeignKey(
        Tag,
        related_name="skill_tags",
        on_delete=models.PROTECT,
        verbose_name=_("Tag")
    )

    skill = models.ForeignKey(
        Skill,
        on_delete=models.PROTECT,
        related_name="skill_tags",
        verbose_name=_("Skill")
    )

    class Meta:
        verbose_name = _("Skill Tag")
        verbose_name_plural = _("Skill Tags")
        unique_together = ("tag", "skill")

    def __str__(self):
        return self.skill.name

    @classmethod
    def is_owned(cls):
        return False
