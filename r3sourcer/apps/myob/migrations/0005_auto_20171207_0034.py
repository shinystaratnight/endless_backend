# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-12-06 13:34
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('myob', '0004_auto_20171206_2044'),
    ]

    operations = [
        migrations.AlterField(
            model_name='myobcompanyfiletoken',
            name='company_file',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tokens', to='myob.MYOBCompanyFile'),
        ),
    ]
