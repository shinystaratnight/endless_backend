# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-02-16 10:33
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_auto_20180208_1938'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='is_system',
            field=models.BooleanField(default=False, editable=False, verbose_name='System Company'),
        ),
    ]
