# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-06-18 08:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0037_company_short_name_default'),
    ]

    operations = [
        migrations.AlterField(
            model_name='company',
            name='short_name',
            field=models.CharField(blank=True, help_text='Used for Jobsite naming', max_length=63, null=True, unique=True, verbose_name='Short name'),
        ),
    ]
