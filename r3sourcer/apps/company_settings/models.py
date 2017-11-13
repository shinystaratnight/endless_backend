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
