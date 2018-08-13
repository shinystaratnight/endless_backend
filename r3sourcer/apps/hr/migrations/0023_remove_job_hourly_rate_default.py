# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-08-07 13:39
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0022_move_job_default_rate'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='job',
            name='hourly_rate_default',
        ),
        migrations.RenameField(
            model_name='job',
            old_name='default_rate',
            new_name='hourly_rate_default'
        )
    ]
