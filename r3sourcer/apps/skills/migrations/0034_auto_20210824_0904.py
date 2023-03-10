# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-08-24 09:04
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('skills', '0033_auto_20210727_1102'),
    ]

    operations = [
        migrations.AlterField(
            model_name='skillraterange',
            name='worktype',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='skill_rate_ranges', to='skills.WorkType', verbose_name='Skill Activity'),
        ),
    ]
