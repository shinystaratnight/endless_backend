# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-03-03 16:20
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0051_timesheet_wage_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='timesheet',
            name='job_offer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='time_sheets', to='hr.JobOffer', unique=True, verbose_name='Job Offer'),
        ),
        migrations.AlterField(
            model_name='timesheet',
            name='shift_ended_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Shift Ended at'),
        ),
        migrations.AlterField(
            model_name='timesheet',
            name='shift_started_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Shift Started at'),
        ),
        migrations.AlterUniqueTogether(
            name='timesheet',
            unique_together=set([]),
        ),
    ]
