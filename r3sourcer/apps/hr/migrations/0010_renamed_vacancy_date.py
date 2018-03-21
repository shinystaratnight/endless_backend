# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-03-19 09:13
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('skills', '0005_skill_rate_unique_together'),
        ('hr', '0009_create_rules'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vacancydate',
            name='hourly_rate',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='shift_dates', to='skills.SkillBaseRate', verbose_name='Hourly rate'),
        ),
        migrations.AlterField(
            model_name='vacancydate',
            name='vacancy',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shift_dates', to='hr.Vacancy', verbose_name='Vacancy'),
        ),
        migrations.RenameModel(old_name='VacancyDate', new_name='ShiftDate'),
        migrations.AlterModelOptions(
            name='shiftdate',
            options={'verbose_name': 'Shift Date', 'verbose_name_plural': 'Shift Dates'},
        ),
        migrations.AlterField(
            model_name='shift',
            name='date',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shifts', to='hr.ShiftDate', verbose_name='Date'),
        ),
    ]