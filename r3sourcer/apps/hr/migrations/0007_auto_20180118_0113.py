# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-01-17 14:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0006_auto_20180117_1800'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contactjobsitedistancecache',
            name='distance',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='contactjobsitedistancecache',
            name='time',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
