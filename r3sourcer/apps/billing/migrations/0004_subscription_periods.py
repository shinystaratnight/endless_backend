# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-07-16 06:04
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0003_smsbalance_one2one'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscription',
            name='current_period_end',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='current_period_start',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
