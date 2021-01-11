# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-01-05 07:05
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('candidate', '0043_tax_number_restore'),
    ]

    operations = [
        migrations.AlterField(
            model_name='formality',
            name='candidate_contact',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='formalities', to='candidate.CandidateContact', verbose_name='Contact'),
        ),
    ]
