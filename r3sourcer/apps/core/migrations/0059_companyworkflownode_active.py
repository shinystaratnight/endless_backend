# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-07-12 08:08
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0058_auto_20180712_0137'),
    ]

    operations = [
        migrations.AddField(
            model_name='companyworkflownode',
            name='active',
            field=models.BooleanField(default=True, verbose_name='Active'),
        ),
    ]
