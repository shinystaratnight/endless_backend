# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-08-21 09:40
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0028_auto_20210821_0931'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='pricelistrate',
            name='skill',
        ),
    ]
