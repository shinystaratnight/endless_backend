# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-09-06 16:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0126_auto_20200727_1846'),
    ]

    operations = [
        migrations.AddField(
            model_name='vat',
            name='stripe_id',
            field=models.CharField(default=1, max_length=64, verbose_name='Stripe ID'),
            preserve_default=False,
        ),
    ]
