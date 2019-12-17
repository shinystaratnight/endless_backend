# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2019-12-11 16:21
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0093_change_created_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='company',
            name='industries',
            field=models.ManyToManyField(blank=True, through='core.CompanyIndustryRel', to='pricing.Industry', verbose_name='Industries'),
        ),
        migrations.AlterField(
            model_name='country',
            name='country_timezone',
            field=models.CharField(blank=True, default='UTC', max_length=255, verbose_name='Country Timezone'),
        ),
        migrations.AlterField(
            model_name='user',
            name='date_joined',
            field=models.DateTimeField(verbose_name='date joined'),
        ),
        migrations.AlterField(
            model_name='user',
            name='trial_period_start',
            field=models.DateTimeField(blank=True, null=True, verbose_name='trial start'),
        ),
    ]
