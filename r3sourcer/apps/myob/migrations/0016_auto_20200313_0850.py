# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-03-13 08:50
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myob', '0015_auto_20191212_1443'),
    ]

    operations = [
        migrations.AlterField(
            model_name='myobcompanyfile',
            name='cf_id',
            field=models.CharField(max_length=64, verbose_name='Company File Id'),
        ),
    ]