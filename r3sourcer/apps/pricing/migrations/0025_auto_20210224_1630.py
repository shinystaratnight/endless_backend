# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-02-24 16:30
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('skills', '0026_auto_20210224_1615'),
        ('pricing', '0024_add_worktype'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='pricelistrate',
            unique_together=set([('price_list', 'skill', 'worktype')]),
        ),
        migrations.RemoveField(
            model_name='pricelistrate',
            name='uom',
        ),
    ]