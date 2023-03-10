# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-11-24 12:03
from __future__ import unicode_literals

from django.db import migrations, models


def delete_duplicates(apps, schema_editor):
    PriceListRate = apps.get_model("pricing", "PriceListRate")
    rate_list = PriceListRate.objects.values('price_list', 'skill', 'hourly_rate').annotate(models.Count('pk'))

    for rate in rate_list:
        if rate['pk__count'] > 1:
            rates_to_delete = PriceListRate.objects.filter(hourly_rate=rate['hourly_rate'],
                                                           price_list=rate['price_list'],
                                                           skill=rate['skill'])[:rate['pk__count'] - 1]
            pk_list = [x.pk for x in rates_to_delete]
            PriceListRate.objects.filter(pk__in=pk_list).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('skills', '0003_add_skillbaserate_defaultrate'),
        ('pricing', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(delete_duplicates),
    ]
