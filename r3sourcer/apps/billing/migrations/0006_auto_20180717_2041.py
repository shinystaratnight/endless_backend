# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-07-17 10:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0005_payment_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='invoice_url',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='payment',
            name='status',
            field=models.CharField(choices=[('paid', 'Paid'), ('not_paid', 'Not paid')], default='not_paid', max_length=255),
        ),
    ]
