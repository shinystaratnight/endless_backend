# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-06-22 13:40
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('candidate', '0008_skillrel_default_rate'),
    ]

    operations = [
        migrations.AddField(
            model_name='skillrel',
            name='active',
            field=models.BooleanField(default=True, verbose_name='Active'),
        ),
    ]
