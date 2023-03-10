# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-06-27 14:16
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('skills', '0007_skill_rate_limits'),
    ]

    operations = [
        migrations.AddField(
            model_name='skill',
            name='price_list_default_rate',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True),
        ),
        migrations.AddField(
            model_name='skill',
            name='price_list_lower_rate_limit',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True),
        ),
        migrations.AddField(
            model_name='skill',
            name='price_list_upper_rate_limit',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True),
        ),
    ]
