from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices

from r3sourcer.apps.core.models import UUIDModel, Contact

from .mixins import GenerateAuthTokenMixin


class TokenLogin(UUIDModel,
                 models.Model,
                 GenerateAuthTokenMixin):

    TYPES = Choices(
        (0, 'sms', _('SMS')),
        (1, 'email', _('E-mail')),
    )

    TYPE_TO_LEN_MAPPING = {
        TYPES.sms: 8,
        TYPES.email: 32,
    }

    contact = models.ForeignKey(
        Contact,
        related_name="extranet_logins",
        verbose_name=_("Contact"),
    )

    auth_token = models.CharField(
        max_length=32,
        verbose_name=_('Auth Token'),
        unique=True
    )

    loggedin_at = models.DateTimeField(
        verbose_name=_('Logged in at'),
        null=True,
        blank=True,
    )

    redirect_to = models.CharField(
        max_length=127,
        verbose_name=_("Redirect Url"),
        default='/'
    )

    type = models.SmallIntegerField(
        choices=TYPES,
        default=TYPES.sms,
        verbose_name=_('Token type')
    )

    class Meta:
        verbose_name = _("Token Login")
        verbose_name_plural = _("Token Logins")

    def __str__(self):
        return 'Token Login {}'.format(self.contact)

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.auth_token = self.generate_auth_token(
                length=self.TYPE_TO_LEN_MAPPING[self.type]
            )

        super(TokenLogin, self).save(*args, **kwargs)

    @property
    def auth_url(self):
        return '/login/{}'.format(self.auth_token)
