# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-02-24 16:15
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('skills', '0025_worktype_worktypelanguage'),
        ('hr', '0049_auto_20200515_1812'),
    ]

    operations = [
        migrations.CreateModel(
            name='TimeSheetRate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('value', models.DecimalField(decimal_places=2, default=0, max_digits=8, verbose_name='Timesheet Value')),
                ('rate', models.DecimalField(decimal_places=2, default=0, max_digits=8, verbose_name='Timesheet Rate')),
                ('timesheet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='timesheet_rates', to='hr.TimeSheet', verbose_name='TimeSheet')),
                ('worktype', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='timesheet_rates', to='skills.WorkType', verbose_name='Type of work')),
            ],
            options={
                'verbose_name': 'TimeSheet Rate',
                'verbose_name_plural': 'TimeSheet Rates',
            },
        ),
        migrations.AddField(
            model_name='job',
            name='wage_type',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Hourly wage'), (1, 'Piecework wage'), (2, 'Combined wage')], default=0, verbose_name='Type of wage'),
        ),
        migrations.AddField(
            model_name='timesheet',
            name='worktype_rates',
            field=models.ManyToManyField(blank=True, through='hr.TimeSheetRate', to='skills.WorkType', verbose_name='Activities rates'),
        ),
        migrations.AlterUniqueTogether(
            name='timesheetrate',
            unique_together=set([('worktype', 'timesheet')]),
        ),
    ]
