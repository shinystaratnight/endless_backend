from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
from django.db import models


class CompanySettings(models.Model):
    logo = models.ImageField(null=True, blank=True)
    color_scheme = models.CharField(null=True, blank=True, max_length=32)
    font = models.CharField(null=True, blank=True, max_length=32)
    forwarding_number = models.CharField(null=True, blank=True, max_length=32)
    account_set = models.OneToOneField('AccountSet', blank=True, null=True, related_name='company_settings')

    def save(self, *args, **kwargs):
        if not self.account_set:
            self.account_set = AccountSet.objects.create()
        super(CompanySettings, self).save(*args, **kwargs)


class MYOBAccount(models.Model):
    number = models.CharField(max_length=63)
    name = models.CharField(max_length=63)
    type = models.CharField(max_length=63)
    company_file = models.ForeignKey('myob.MYOBCompanyFile', blank=True, null=True, related_name='accounts')

    def __str__(self):
        return self.number + self.name


class AccountSet(models.Model):
    """
    This model represents list of actions(transactions) that we perform.
    Every our inner account has to point to outer MYOB account.
    """
    # Expense accounts
    subcontractor_contract_work = models.ForeignKey(MYOBAccount, blank=True, null=True, related_name='subcontractor_contract_work')
    subcontractor_gst = models.ForeignKey(MYOBAccount, blank=True, null=True, related_name='subcontractor_gst')
    candidate_wages = models.ForeignKey(MYOBAccount, blank=True, null=True, related_name='candidate_wages')
    candidate_superannuation = models.ForeignKey(MYOBAccount, blank=True, null=True, related_name='candidate_superannuation')

    # Income accounts
    company_client_labour_hire = models.ForeignKey(MYOBAccount, blank=True, null=True, related_name='company_client_labour_hire')
    company_client_gst = models.ForeignKey(MYOBAccount, blank=True, null=True, related_name='company_client_gst')


class GlobalPermissionManager(models.Manager):
    def get_queryset(self):
        return super(GlobalPermissionManager, self).get_queryset().filter(content_type__model='global_permission')


class GlobalPermission(Permission):
    """A global permission, not attached to a model"""

    CONTENT_TYPE = 'global_permission'
    objects = GlobalPermissionManager()

    class Meta:
        proxy = True

    def save(self, *args, **kwargs):
        content_type, _ = ContentType.objects.get_or_create(model=self.CONTENT_TYPE, app_label=self._meta.app_label)
        self.content_type = content_type
        super(GlobalPermission, self).save(*args, **kwargs)
