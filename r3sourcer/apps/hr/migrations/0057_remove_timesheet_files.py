# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-07-10 08:45
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0056_candidatetimesheetfiles_clienttimesheetfiles'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='timesheet',
            name='candidate_notes',
        ),
        migrations.RemoveField(
            model_name='timesheet',
            name='client_notes',
        ),
        migrations.DeleteModel(
            name='CandidateTimeSheetFiles',
        ),
        migrations.DeleteModel(
            name='ClientTimeSheetFiles',
        ),
    ]
