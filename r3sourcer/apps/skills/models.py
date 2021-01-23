from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

from r3sourcer.apps.core.mixins import MYOBMixin
from r3sourcer.apps.core.models import Company, UnitOfMeasurement
from r3sourcer.helpers.models.abs import UUIDModel
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


class SkillName(UUIDModel):

    name = models.CharField(max_length=127, verbose_name=_("Skill Name"))

    industry = models.ForeignKey(
        'pricing.Industry',
        on_delete=models.PROTECT,
        verbose_name=_('Industry'),
        related_name='skill_names'
    )

    class Meta:
        verbose_name = _("Skill Name")
        verbose_name_plural = _("Skill Names")
        unique_together = [
            'name',
            'industry',
        ]

    def __str__(self):
        return self.name

    @classmethod
    def owned_by_lookups(cls, owner):
        if isinstance(owner, Company):
            return [
                models.Q(industry__in=owner.industries.all())
            ]


class SkillNameLanguage(models.Model):
    name = models.ForeignKey(
        'skills.SkillName',
        related_name='translations',
        on_delete=models.PROTECT,
        verbose_name=_('Skill Name'),
    )
    value = models.CharField(max_length=127, verbose_name=_("Skill Name transalation"))
    language = models.ForeignKey(
        'core.Language',
        verbose_name=_("Skill name language"),
        on_delete=models.CASCADE,
        related_name='skill_names',
    )

    class Meta:
        verbose_name = _("Skill Name Language")
        verbose_name_plural = _("Skill Name Languages")
        unique_together = [
            'name',
            'language',
        ]

    def __str__(self):
        return self.value


class Skill(MYOBMixin, UUIDModel):
    name = models.ForeignKey(
        SkillName,
        related_name='skills',
        on_delete=models.PROTECT,
        verbose_name=_('Skill Name'),
    )

    company = models.ForeignKey(
        'core.Company',
        related_name='skills',
        on_delete=models.CASCADE,
        verbose_name=_('Company')
    )

    carrier_list_reserve = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_('Carrier List Reserve')
    )

    short_name = models.CharField(
        max_length=15,
        verbose_name=_("Short Name"),
        help_text=_("Abbreviation, for use by staff reports and dashboards"),
        blank=True,
        null=True
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

    tags = models.ManyToManyField(
        'core.Tag',
        related_name='skills',
        through='SkillTag'
    )

    class Meta:
        verbose_name = _("Skill")
        verbose_name_plural = _("Skills")

    def __str__(self):
        return self.name.name

    def get_myob_name(self):
        name = self.short_name
        if not name:
            parts = self.name.name.split(' ')
            parts_len = len(parts)
            trim_size = 1

            if parts_len == 1:
                trim_size = 6
            elif parts_len == 2 or parts_len == 3:
                trim_size = 6 // parts_len

            name = ''.join([p[:trim_size] for p in parts])

        return name[:6]

    @classmethod
    def owned_by_lookups(cls, owner):
        if isinstance(owner, Company):
            return [
                models.Q(company=owner),
                models.Q(company__regular_companies__master_company=owner)
            ]


class SkillBaseRate(UUIDModel):

    skill = models.ForeignKey(
        'skills.Skill',
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
        'core.Tag',
        related_name="skill_tags",
        on_delete=models.PROTECT,
        verbose_name=_("Tag")
    )

    skill = models.ForeignKey(
        'skills.Skill',
        on_delete=models.PROTECT,
        related_name="skill_tags",
        verbose_name=_("Skill")
    )

    class Meta:
        verbose_name = _("Skill Tag")
        verbose_name_plural = _("Skill Tags")
        unique_together = ("tag", "skill")

    def __str__(self):
        return self.skill.short_name or self.skill.name.name

    @classmethod
    def owned_by_lookups(cls, owner):
        if isinstance(owner, Company):
            return [
                models.Q(skill__company=owner),
                models.Q(skill__company__regular_companies__master_company=owner)
            ]


class SkillRateRange(MYOBMixin, UUIDModel):

    skill = models.ForeignKey(
        Skill,
        related_name="skill_rate_ranges",
        verbose_name=_("Skill")
    )

    uom = models.ForeignKey(
        UnitOfMeasurement,
        related_name='skill_rate_ranges',
        on_delete=models.PROTECT,
        verbose_name=_('Unit of measurement'),
    )

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


    class Meta:
        verbose_name = _("Skill Rate Range")
        verbose_name_plural = _("Skill Rate Ranges")
        unique_together = ("skill", "uom")

    def __str__(self):
        return self.skill.name.name

    def clean(self, *args, **kwargs):
        have_default_base_rate = self.default_rate
        have_default_price_list_rate = self.price_list_default_rate

        if not have_default_base_rate:
            raise ValidationError({'default_rate': ["Please add default base rate."]})
        elif not have_default_price_list_rate and self.skill.company.purpose == 'hire':
            raise ValidationError({'price_list_default_rate': ["Please add default price list rate."]})

        super().clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
