# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-09-23 05:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0029_auto_20210610_0858'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscription',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('past_due', 'Past due'), ('canceled', 'Canceled'), ('unpaid', 'Unpaid'), ('incomplete', 'Incomplete'), ('trialing', 'Trialing'), ('incomplete_expired', 'Incomplete expired')], max_length=255),
        ),
    ]