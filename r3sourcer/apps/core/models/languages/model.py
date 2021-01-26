from django.db import models
from django.utils.translation import ugettext_lazy as _


class AliasField(models.Field):
    # def contribute_to_class(self, cls, name, virtual_only=False):
    #       '''
    #           virtual_only is deprecated in favor of private_only
    #       '''
    #     super(AliasField, self).contribute_to_class(cls, name, virtual_only=True)
    #     setattr(cls, name, self)

    def contribute_to_class(self, cls, name, private_only=False):
        '''
            virtual_only is deprecated in favor of private_only
        '''
        super(AliasField, self).contribute_to_class(cls, name, private_only=True)
        setattr(cls, name, self)

    def __get__(self, instance, instance_type=None):
        return getattr(instance, self.db_column)


class Language(models.Model):
    alpha_2 = models.CharField(max_length=2, primary_key=True)
    name = models.CharField(max_length=64)
    id = AliasField(db_column='alpha_2', unique=True)


    class Meta:
        verbose_name = _("Language")
        verbose_name_plural = _("Languages")

    def __str__(self):
        return self.name
