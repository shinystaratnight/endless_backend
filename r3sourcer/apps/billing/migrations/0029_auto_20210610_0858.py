# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-06-10 08:58
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0028_alter_payment_amount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='smsbalance',
            name='last_payment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='billing.Payment'),
        ),
    ]
