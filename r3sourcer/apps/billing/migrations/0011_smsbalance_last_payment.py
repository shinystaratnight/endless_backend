# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-08-13 10:54
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0010_remove_smsbalance_discount'),
    ]

    operations = [
        migrations.AddField(
            model_name='smsbalance',
            name='last_payment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='billing.Payment'),
        ),
    ]
