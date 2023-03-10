# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-05-15 17:54
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0115_auto_20200515_1744'),
    ]

    operations = [
        migrations.AlterField(
            model_name='companycontactrelationship',
            name='company_contact',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='relationships', to='core.CompanyContact', verbose_name='Company Contact'),
        ),
    ]
