# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-08-07 08:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sms_interface', '0004_smsmessage_company'),
    ]

    operations = [
        migrations.AddField(
            model_name='smsmessage',
            name='segments',
            field=models.IntegerField(blank=True, null=True, verbose_name='Number of segments'),
        ),
    ]
