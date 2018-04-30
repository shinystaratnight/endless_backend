from django.db import models
from model_utils import Choices

from r3sourcer.apps.core.models import Company


class PaymentInformation(models.Model):
    company = models.ForeignKey(Company)
    email = models.CharField(max_length=255)
    token_type = models.CharField(max_length=255)
    token = models.CharField(max_length=255)

    def __str__(self, *args, **kwargs):
        return self.email


class Plan(models.Model):
    TYPE_CHOICES = Choices(
        ('annual', 'Annual'),
        ('monthly', 'Monthly')
    )
    company = models.ForeignKey(Company)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255, choices=TYPE_CHOICES)
    price = models.PositiveIntegerField()
    worker_count = models.PositiveIntegerField()
    created = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        super(Plan, self).save(*args, **kwargs)

        if self.active:
            Plan.objects.filter(company=self.company) \
                        .exclude(id=self.id) \
                        .update(active=False)
