# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-04-25 10:37
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0006_set_rate_coefficient_industry_not_null'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pricelistrate',
            name='price_list',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='price_list_rates', to='pricing.PriceList', verbose_name='Price List'),
        ),
    ]
