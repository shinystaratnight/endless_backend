# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-06-15 12:44
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0017_added_job_tags'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='jobtag',
            name='verification_evidence',
        ),
        migrations.RemoveField(
            model_name='jobtag',
            name='verified_by',
        ),
    ]
