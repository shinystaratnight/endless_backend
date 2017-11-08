from django.db import models


class CompanySettings(models.Model):
    logo = models.ImageField(null=True, blank=True)
    color_scheme = models.CharField(null=True, blank=True, max_length=32)
    font = models.CharField(null=True, blank=True, max_length=32)
    forwarding_number = models.CharField(null=True, blank=True, max_length=32)
