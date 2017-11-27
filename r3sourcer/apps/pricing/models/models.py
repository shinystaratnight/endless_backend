from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.utils.formats import date_format
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices

from r3sourcer.apps.core.models import UUIDModel, Company, CompanyContact
from r3sourcer.apps.skills.models import Skill
from r3sourcer.apps.pricing.models.rules import all_rules


class PriceListMixin(models.Model):

    valid_from = models.DateField(
        verbose_name=_('Valid From'),
        auto_now_add=True,
    )

    valid_until = models.DateField(
        verbose_name=_('Valid Until'),
        null=True,
        blank=True,
    )

    effective = models.BooleanField(
        verbose_name=_('Effective'),
        default=False,
    )

    class Meta:
        abstract = True


class PriceListRateMixin(models.Model):

    hourly_rate = models.DecimalField(
        decimal_places=2,
        max_digits=16,
        verbose_name=_("Hourly Rate"),
        default=0.00
    )

    class Meta:
        abstract = True


class Industry(UUIDModel):

    type = models.CharField(
        max_length=63,
        verbose_name=_('Type'),
    )

    class Meta:
        verbose_name = _('Industry')
        verbose_name_plural = _('Industries')

    def __str__(self):
        return self.type


class RateCoefficientGroup(UUIDModel):

    name = models.CharField(
        max_length=255,
        verbose_name=_("Name"),
    )

    class Meta:
        verbose_name = _("Rate Coefficient Group")
        verbose_name_plural = _("Rate Coefficient Groups")

    def __str__(self):
        return self.name


class RateCoefficient(UUIDModel):

    name = models.CharField(
        max_length=18,
        verbose_name=_("Name"),
        unique=True,
    )

    group = models.ForeignKey(
        RateCoefficientGroup,
        related_name='rate_coefficients',
        on_delete=models.PROTECT,
        verbose_name=_("Group"),
        help_text=_("Group coefficients across industries"),
        blank=True,
        null=True,
    )

    active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
    )

    priority = models.PositiveIntegerField(
        verbose_name=_('Priority'),
        default=0,
        editable=False,
    )

    class Meta:
        verbose_name = _("Rate Coefficient")
        verbose_name_plural = _("Rate Coefficients")

    def __str__(self):
        return self.name


class IndustryPriceList(PriceListMixin, UUIDModel):

    industry = models.ForeignKey(
        Industry,
        on_delete=models.PROTECT,
        related_name='industry_price_lists',
        verbose_name=_('Industry'),
    )

    industry_rate_coefficients = models.ManyToManyField(
        RateCoefficient,
        related_name='industry_price_lists',
        verbose_name=_('Industry Rate Coefficients'),
        through='IndustryRateCoefficient',
    )

    class Meta:
        verbose_name = _('Industry Price List')
        verbose_name_plural = _('Industry Price Lists')

    def __str__(self):
        res = '{}: {}'.format(
            str(self.industry),
            date_format(self.valid_from, settings.DATE_FORMAT),
        )

        if self.valid_until:
            res = '{} - {}'.format(
                res,
                date_format(self.valid_until, settings.DATE_FORMAT),
            )

        return res


class IndustryPriceListRate(PriceListRateMixin, UUIDModel):

    industry_price_list = models.ForeignKey(
        IndustryPriceList,
        on_delete=models.PROTECT,
        related_name='industry_price_list_rates',
        verbose_name=_('Industry Price List'),
    )

    skill = models.ForeignKey(
        Skill,
        on_delete=models.PROTECT,
        related_name='industry_price_list_rates',
        verbose_name=_('Skill'),
    )

    class Meta:
        verbose_name = _('Industry Price List Rate')
        verbose_name_plural = _('Industry Price List Rates')

    def __str__(self):
        return _('{}: ${}/h').format(str(self.skill), str(self.hourly_rate))


class IndustryRateCoefficient(UUIDModel):

    industry_price_list = models.ForeignKey(
        IndustryPriceList,
        on_delete=models.PROTECT,
        verbose_name=_('Industry Price List'),
    )

    rate_coefficient = models.ForeignKey(
        RateCoefficient,
        on_delete=models.PROTECT,
        verbose_name=_('Rate Coefficient'),
    )

    class Meta:
        unique_together = ('industry_price_list', 'rate_coefficient')


class PriceList(PriceListMixin, UUIDModel):

    industry_price_list = models.ForeignKey(
        IndustryPriceList,
        on_delete=models.PROTECT,
        related_name='price_lists',
        verbose_name=_('Industry Price List'),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name='price_lists',
        verbose_name=_('Company'),
    )

    approved_by = models.ForeignKey(
        CompanyContact,
        related_name="price_lists",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Approved By")
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Approved At")
    )

    rate_coefficients = models.ManyToManyField(
        RateCoefficient,
        related_name='price_lists',
        verbose_name=_('Rate Coefficients'),
        through='PriceListRateCoefficient',
    )

    class Meta:
        verbose_name = _('Price List')
        verbose_name_plural = _('Price Lists')

    def __str__(self):
        res = '{}: {}'.format(
            str(self.company),
            date_format(self.valid_from, settings.DATE_FORMAT),
        )

        if self.valid_until:
            res = '{} - {}'.format(
                res,
                date_format(self.valid_until, settings.DATE_FORMAT),
            )

        return res


class PriceListRate(PriceListRateMixin, UUIDModel):

    price_list = models.ForeignKey(
        PriceList,
        on_delete=models.PROTECT,
        related_name='price_list_rates',
        verbose_name=_('Price List'),
    )

    skill = models.ForeignKey(
        Skill,
        on_delete=models.PROTECT,
        related_name='price_list_rates',
        verbose_name=_('Skill'),
    )

    default_rate = models.BooleanField(
        default=False,
        verbose_name=_("Is Default Rate")
    )

    class Meta:
        verbose_name = _('Price List Rate')
        verbose_name_plural = _('Price List Rates')
        unique_together = ('price_list', 'skill', 'hourly_rate')

    @classmethod
    def set_default_rate(cls, sender, instance, created, **kwargs):
        if created and not instance.skill.price_list_rates.exclude(pk=instance.pk).count():
            instance.default_rate = True
            instance.save()

    def clean(self, *args, **kwargs):
        if self.default_rate:
            default_rates = self.skill.price_list_rates.filter(default_rate=True) \
                                                       .exclude(pk=self.pk)
            if default_rates.count():
                raise ValidationError('Only one rate for the skill can be set to "True"')

        super(PriceListRate, self).clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.full_clean()

        if not self.pk and self.skill.price_list_rates.count():
            self.default_rate = True

        super(PriceListRate, self).save(*args, **kwargs)

    def __str__(self):
        return _('{}: ${}/h').format(str(self.skill), str(self.hourly_rate))


class PriceListRateCoefficient(UUIDModel):

    price_list = models.ForeignKey(
        PriceList,
        on_delete=models.PROTECT,
        verbose_name=_('Price List'),
    )

    rate_coefficient = models.ForeignKey(
        RateCoefficient,
        on_delete=models.PROTECT,
        verbose_name=_('Rate Coefficient'),
    )

    class Meta:
        unique_together = ('price_list', 'rate_coefficient')


class RateCoefficientModifier(UUIDModel):

    TYPE_CHOICES = Choices(
        (0, 'company', _('Company')),
        (1, 'candidate', _('Candidate')),
    )

    type = models.PositiveSmallIntegerField(
        choices=TYPE_CHOICES,
        verbose_name=_('Type'),
    )

    rate_coefficient = models.ForeignKey(
        RateCoefficient,
        on_delete=models.PROTECT,
        related_name='rate_coefficient_modifiers',
        verbose_name=_('Rate Coefficient'),
    )

    multiplier = models.DecimalField(
        decimal_places=2,
        max_digits=4,
        default=1.00,
        verbose_name=_("Multiplier"),
        help_text=_("1.00 = none"),
    )

    fixed_addition = models.DecimalField(
        decimal_places=2,
        max_digits=16,
        default=0,
        verbose_name=_("Fixed Addition"),
        help_text=_("adds after multiplying when set"),
    )

    fixed_override = models.DecimalField(
        decimal_places=2,
        max_digits=16,
        default=0,
        verbose_name=_("Fixed Rate Override"),
    )

    class Meta:
        verbose_name = _('Rate Coefficient Modifier')
        verbose_name_plural = _('Rate Coefficient Modifiers')

    def __str__(self):
        if self.fixed_override:
            return '{}: ${}/h'.format(str(self.rate_coefficient),
                                      str(self.fixed_override))
        return '{}: *{}+{}'.format(
            str(self.rate_coefficient), str(self.multiplier),
            str(self.fixed_addition)
        )

    def calc(self, hourly_rate):
        if self.fixed_override > 0:
            return self.fixed_override
        else:
            return hourly_rate * self.multiplier + self.fixed_addition


class DynamicCoefficientRule(UUIDModel):

    rate_coefficient = models.ForeignKey(
        RateCoefficient,
        on_delete=models.PROTECT,
        related_name='rate_coefficient_rules',
        verbose_name=_('Rate Coefficient'),
    )

    priority = models.PositiveSmallIntegerField(
        verbose_name=_('Rule Priority'),
        default=0,
    )

    rule_type = models.ForeignKey(
        ContentType,
        limit_choices_to=Q(app_label='pricing',
                           model__in=all_rules),
        on_delete=models.CASCADE
    )
    rule_id = models.UUIDField()
    rule = GenericForeignKey('rule_type', 'rule_id')

    class Meta:
        verbose_name = _("Dynamic Coefficient Rule")
        verbose_name_plural = _("Dynamic Coefficient Rules")

    def __str__(self):
        return '{}: {}'.format(str(self.rate_coefficient), self.rule_type.name)

    def save(self, *args, **kwargs):
        if self._state.adding:
            if self.priority == 0:
                self.priority = getattr(self.rule, 'default_priority', 0)

            self.rate_coefficient.priority += self.priority
            self.rate_coefficient.save()

        super().save(*args, **kwargs)


__all__ = [
    'PriceListMixin', 'PriceListRateMixin', 'Industry', 'RateCoefficientGroup',
    'RateCoefficient', 'IndustryPriceList', 'IndustryPriceListRate',
    'IndustryRateCoefficient', 'PriceList', 'PriceListRate',
    'PriceListRateCoefficient', 'RateCoefficientModifier',
    'DynamicCoefficientRule',
]


post_save.connect(PriceListRate.set_default_rate, sender=PriceListRate)
