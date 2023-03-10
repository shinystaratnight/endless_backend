# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-02-08 09:18
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0005_added_industry_to_rate_coefficient'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ratecoefficient',
            name='industry',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='rate_coefficients', to='pricing.Industry', verbose_name='Industry'),
        ),
    ]
