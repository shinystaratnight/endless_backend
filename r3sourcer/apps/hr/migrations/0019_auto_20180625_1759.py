# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-06-25 07:59
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0018_removed_jobtags_verification'),
    ]

    operations = [
        migrations.AlterField(
            model_name='blacklist',
            name='company',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blacklists', to='core.Company', verbose_name='Company'),
        ),
        migrations.AlterField(
            model_name='job',
            name='customer_company',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='customer_jobs', to='core.Company', verbose_name='Customer Company'),
        ),
        migrations.AlterField(
            model_name='payslip',
            name='company',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payslips', to='core.Company', verbose_name='Company'),
        ),
        migrations.AlterField(
            model_name='paysliprule',
            name='company',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payslip_rules', to='core.Company', verbose_name='Company'),
        ),
    ]
