# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2019-04-02 16:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0012_added_used_field_to_rules'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='allowanceworkrule',
            name='used',
        ),
        migrations.RemoveField(
            model_name='overtimeworkrule',
            name='used',
        ),
        migrations.RemoveField(
            model_name='timeofdayworkrule',
            name='used',
        ),
        migrations.AddField(
            model_name='dynamiccoefficientrule',
            name='used',
            field=models.BooleanField(default=False),
        ),
    ]
