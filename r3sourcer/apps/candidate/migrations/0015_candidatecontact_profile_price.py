# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-07-20 08:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('candidate', '0014_default_candidate_relation'),
    ]

    operations = [
        migrations.AddField(
            model_name='candidatecontact',
            name='profile_price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8, verbose_name='Profile Price'),
        ),
    ]
