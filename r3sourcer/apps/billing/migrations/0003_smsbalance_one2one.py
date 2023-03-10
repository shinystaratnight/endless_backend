# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-07-10 12:26
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


def update_company_fields(apps, schema_editor):
    Company = apps.get_model("core", "Company")
    companies = Company.objects.all()
    companies = [company.save() for company in companies]


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_payment_company'),
    ]

    operations = [
        migrations.AlterField(
            model_name='smsbalance',
            name='company',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sms_balance', to='core.Company'),
        ),
        migrations.RunPython(update_company_fields)
    ]
