# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-01-18 15:36
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0007_auto_20180118_0113'),
    ]

    operations = [
        migrations.AddField(
            model_name='candidatescore',
            name='average_score',
            field=models.DecimalField(decimal_places=2, editable=False, max_digits=3, null=True, verbose_name='Average Score'),
        ),
    ]