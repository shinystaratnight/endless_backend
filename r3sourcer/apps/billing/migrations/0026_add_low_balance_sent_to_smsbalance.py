# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-01-27 06:37
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0025_load_sms_balance_limits_fixtures'),
    ]

    operations = [
        migrations.AddField(
            model_name='smsbalance',
            name='low_balance_sent',
            field=models.BooleanField(default=False),
        ),
    ]