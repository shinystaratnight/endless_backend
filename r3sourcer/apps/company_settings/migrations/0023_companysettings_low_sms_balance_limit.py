# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-12-15 04:14
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company_settings', '0022_companysettings_allow_job_creation'),
    ]

    operations = [
        migrations.AddField(
            model_name='companysettings',
            name='low_sms_balance_limit',
            field=models.PositiveIntegerField(default=20),
        ),
    ]