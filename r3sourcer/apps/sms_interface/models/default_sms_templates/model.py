from django.db import models
from django.utils.translation import ugettext_lazy as _

from ..sms_templates import SMSTemplate


class DefaultSMSTemplate(models.Model):
    name = models.CharField(
        max_length=256,
        default="",
        verbose_name=_("Name"),
        db_index=True
    )
    slug = models.SlugField()
    message_text_template = models.TextField(
        default="",
        verbose_name=_("Text template"),
    )

    reply_timeout = models.IntegerField(
        default=10,
        verbose_name=_("Reply timeout"),
        help_text=_("Minutes")
    )

    delivery_timeout = models.IntegerField(
        default=10,
        verbose_name=_("Delivery timeout"),
        help_text=_("Minutes")
    )
    language = models.ForeignKey(
        'core.Language',
        verbose_name=_("Language"),
        on_delete=models.PROTECT,
        related_name='default_sms_templates',
        db_index=True,
    )

    class Meta:
        verbose_name = _("Default SMS Template")
        verbose_name_plural = _("Default SMS Templates")
        unique_together = (('slug', 'language'),)
        ordering = ['name']

    def save(self, *args, **kwargs):
        from r3sourcer.apps.core.models import Company
        super().save(*args, **kwargs)
        templates = []
        for company in Company.objects.filter(
                    type=Company.COMPANY_TYPES.master,
                    languages__language=self.language
                ).exclude(
                    sms_templates__slug=self.slug,
                ).all():
            obj = SMSTemplate(
                name=self.name,
                slug=self.slug,
                message_text_template=self.message_text_template,
                reply_timeout=self.reply_timeout,
                delivery_timeout=self.delivery_timeout,
                language_id=self.language.alpha_2,
                company_id=company.id)
            templates.append(obj)
        SMSTemplate.objects.bulk_create(templates)
