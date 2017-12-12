# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-12-07 17:23
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('company_settings', '0004_add_accountset_model'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='accountset',
            name='candidate_superannuation',
        ),
        migrations.RemoveField(
            model_name='accountset',
            name='candidate_wages',
        ),
        migrations.RemoveField(
            model_name='accountset',
            name='company_client_gst',
        ),
        migrations.RemoveField(
            model_name='accountset',
            name='company_client_labour_hire',
        ),
        migrations.RemoveField(
            model_name='accountset',
            name='subcontractor_contract_work',
        ),
        migrations.RemoveField(
            model_name='accountset',
            name='subcontractor_gst',
        ),
        migrations.RemoveField(
            model_name='companysettings',
            name='account_set',
        ),
        migrations.RemoveField(
            model_name='companysettings',
            name='color_scheme',
        ),
        migrations.RemoveField(
            model_name='companysettings',
            name='logo',
        ),
        migrations.DeleteModel(
            name='AccountSet',
        ),
        migrations.DeleteModel(
            name='MYOBAccount',
        ),
    ]
