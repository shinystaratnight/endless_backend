# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2019-06-02 15:09
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0017_ratecoefficientmodifier_set_default'),
    ]

    operations = [
        migrations.CreateModel(
            name='PriceListRateModifier',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('price_list_rate', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='price_list_rate_modifiers', to='pricing.PriceListRate', verbose_name='Price List Rate')),
                ('rate_coefficient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='price_list_rate_modifiers', to='pricing.RateCoefficient', verbose_name='Rate coefficient')),
                ('rate_coefficient_modifier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='price_list_rate_modifiers', to='pricing.RateCoefficientModifier', verbose_name='Rate coefficient modifier')),
            ],
            options={
                'verbose_name_plural': 'Price List Rate Coefficient Relations',
                'verbose_name': 'Price List Rate Coefficient Relation',
            },
        ),
        migrations.AlterUniqueTogether(
            name='pricelistratemodifier',
            unique_together=set([('price_list_rate', 'rate_coefficient', 'rate_coefficient_modifier')]),
        ),
    ]