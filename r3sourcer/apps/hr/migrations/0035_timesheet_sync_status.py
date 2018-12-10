# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-12-10 14:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0034_change_on_delete_for_candidates'),
    ]

    operations = [
        migrations.AddField(
            model_name='timesheet',
            name='sync_status',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Not synced'), (1, 'Sync scheduled'), (2, 'Syncing...'), (3, 'Synced'), (4, 'Sync failed')], default=0, verbose_name='Sync status'),
        ),
    ]
