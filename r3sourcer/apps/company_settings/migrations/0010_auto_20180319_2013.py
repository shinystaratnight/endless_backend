# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-03-19 09:13
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('company_settings', '0009_create_uuid_models'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='companysettings',
            options={'verbose_name': 'Company settings', 'verbose_name_plural': 'Company settings'},
        ),
        migrations.AlterModelOptions(
            name='myobsettings',
            options={'verbose_name': 'MYOB settings', 'verbose_name_plural': 'MYOB settings'},
        ),
    ]
