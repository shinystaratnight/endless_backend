# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-07-17 12:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company_settings', '0013_grant_permissions_to_clients'),
    ]

    operations = [
        migrations.AddField(
            model_name='companysettings',
            name='billing_email',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
