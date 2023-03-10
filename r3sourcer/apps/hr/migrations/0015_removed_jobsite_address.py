# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-03-26 12:25
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0014_copy_address_to_jobsite'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='jobsiteaddress',
            name='address',
        ),
        migrations.RemoveField(
            model_name='jobsiteaddress',
            name='jobsite',
        ),
        migrations.RemoveField(
            model_name='jobsiteaddress',
            name='regular_company',
        ),
        migrations.AlterField(
            model_name='jobsite',
            name='regular_company',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='jobsites_regular', to='core.Company', verbose_name='Client'),
        ),
        migrations.DeleteModel(
            name='JobsiteAddress',
        ),
    ]
