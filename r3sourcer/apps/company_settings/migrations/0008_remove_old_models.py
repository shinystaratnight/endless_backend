# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-12-14 17:38
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('company_settings', '0007_add_refreshed_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='companysettings',
            name='company',
        ),
        migrations.RemoveField(
            model_name='myobaccount',
            name='company_file',
        ),
        migrations.RemoveField(
            model_name='myobsettings',
            name='candidate_superannuation',
        ),
        migrations.RemoveField(
            model_name='myobsettings',
            name='candidate_wages',
        ),
        migrations.RemoveField(
            model_name='myobsettings',
            name='company',
        ),
        migrations.RemoveField(
            model_name='myobsettings',
            name='company_client_gst',
        ),
        migrations.RemoveField(
            model_name='myobsettings',
            name='company_client_labour_hire',
        ),
        migrations.RemoveField(
            model_name='myobsettings',
            name='subcontractor_contract_work',
        ),
        migrations.RemoveField(
            model_name='myobsettings',
            name='subcontractor_gst',
        ),
        migrations.DeleteModel(
            name='CompanySettings',
        ),
        migrations.DeleteModel(
            name='MYOBAccount',
        ),
        migrations.DeleteModel(
            name='MYOBSettings',
        ),
    ]
