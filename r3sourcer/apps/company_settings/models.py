from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
from django.db import models


class CompanySettings(models.Model):
    company = models.OneToOneField('core.Company', blank=True, null=True, related_name='company_settings')
    logo = models.ImageField(null=True, blank=True)
    color_scheme = models.CharField(null=True, blank=True, max_length=32)
    font = models.CharField(null=True, blank=True, max_length=32)
    forwarding_number = models.CharField(null=True, blank=True, max_length=32)
    account_set = models.OneToOneField('MYOBSettings', blank=True, null=True, related_name='company_settings')


class MYOBAccount(models.Model):
    uid = models.UUIDField(unique=True)
    name = models.CharField(max_length=63)
    display_id = models.CharField(max_length=63)
    classification = models.CharField(max_length=63)
    type = models.CharField(max_length=63)
    number = models.CharField(max_length=63)
    description = models.CharField(max_length=255)
    is_active = models.BooleanField()
    level = models.IntegerField()
    opening_balance = models.DecimalField(decimal_places=2, max_digits=16)
    current_balance = models.DecimalField(decimal_places=2, max_digits=16)
    is_header = models.BooleanField()
    uri = models.CharField(max_length=255)
    row_version = models.CharField(max_length=255)
    company_file = models.ForeignKey('myob.MYOBCompanyFile', blank=True, null=True, related_name='accounts')

    def __str__(self):
        return self.number + self.name


class MYOBSettings(models.Model):
    company = models.OneToOneField('core.Company', blank=True, null=True, related_name='myob_settings')

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
