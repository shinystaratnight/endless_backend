from django.db import models
from django.utils.translation import ugettext_lazy as _


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
