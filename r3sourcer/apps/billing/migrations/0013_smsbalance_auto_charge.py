# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-09-11 07:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0012_smsbalance_cost_of_segment'),
    ]

    operations = [
        migrations.AddField(
            model_name='smsbalance',
            name='auto_charge',
            field=models.BooleanField(default=False, verbose_name='Auto Charge'),
            ),
        ]
