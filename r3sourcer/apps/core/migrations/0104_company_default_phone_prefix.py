# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-03-24 10:03
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0103_auto_20200321_1807'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='default_phone_prefix',
            field=models.CharField(blank=True, max_length=3, null=True),
        ),
    ]
