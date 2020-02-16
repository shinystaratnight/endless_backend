# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-01-30 20:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0095_auto_20191212_1437'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='sync_status',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Not synced'), (1, 'Sync scheduled'), (2, 'Syncing...'), (3, 'Synced'), (4, 'Sync failed')], default=0, verbose_name='Sync status'),
        ),
    ]