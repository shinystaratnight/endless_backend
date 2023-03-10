# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-03-28 13:26
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('company_settings', '0011_update_myob_settings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='myobsettings',
            name='invoice_activity_account',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='company_settings.MYOBAccount'),
        ),
        migrations.AlterField(
            model_name='myobsettings',
            name='invoice_company_file',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invoice_company_files', to='myob.MYOBCompanyFile'),
        ),
        migrations.AlterField(
            model_name='myobsettings',
            name='timesheet_company_file',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='timesheet_company_files', to='myob.MYOBCompanyFile'),
        ),
    ]
