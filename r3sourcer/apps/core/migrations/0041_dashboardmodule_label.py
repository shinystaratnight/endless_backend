# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-06-19 09:07
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0040_created_dashboard_4_buttons'),
    ]

    operations = [
        migrations.AddField(
            model_name='dashboardmodule',
            name='label',
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name='Button label'),
        ),
    ]
