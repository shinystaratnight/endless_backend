# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-09-05 11:35
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('acceptance_tests', '0008_remove_acceptancetestworkflownode_score'),
    ]

    operations = [
        migrations.AlterField(
            model_name='acceptancetest',
            name='valid_until',
            field=models.DateField(blank=True, null=True, verbose_name='Valid Until'),
        ),
    ]
