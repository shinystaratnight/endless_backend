from django.db import models
from django.utils.translation import ugettext_lazy as _


class CompanyLanguage(models.Model):
    company = models.ForeignKey(
        'core.Company',
        related_name="languages",
        verbose_name=_("Company"),
        on_delete=models.CASCADE)

    language = models.ForeignKey(
        'core.Language',
        related_name="company_languages",
        verbose_name=_("Language"),
        on_delete=models.PROTECT)

    default = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Company language")
        verbose_name_plural = _("Company languages")
        unique_together = (("company", "language"),)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):

        if self.default is True:
            CompanyLanguage.objects.filter(company=self.company, default=True).update(default=False)

        super().save(force_insert, force_update, using, update_fields)
        # add steps for adding company templates
