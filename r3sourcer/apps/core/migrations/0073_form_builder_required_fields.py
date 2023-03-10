# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-11-26 09:14
from __future__ import unicode_literals

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0072_set_contact_relations'),
    ]

    operations = [
        migrations.AddField(
            model_name='formbuilder',
            name='active_fields',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None, verbose_name='Default active fields'),
        ),
        migrations.AddField(
            model_name='formbuilder',
            name='required_fields',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None, verbose_name='Required fields'),
        ),
    ]
