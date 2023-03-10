# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-11-17 15:27
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0030_auto_20210824_0905'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pricelistratemodifier',
            name='rate_coefficient',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='price_list_rate_modifiers', to='pricing.RateCoefficient', verbose_name='Rate coefficient'),
        ),
        migrations.AlterField(
            model_name='pricelistratemodifier',
            name='rate_coefficient_modifier',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='price_list_rate_modifiers', to='pricing.RateCoefficientModifier', verbose_name='Rate coefficient modifier'),
        ),
        migrations.AlterField(
            model_name='ratecoefficientrel',
            name='rate_coefficient',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='rate_coefficient_rels', to='pricing.RateCoefficient', verbose_name='Rate Coefficient'),
        ),
    ]
