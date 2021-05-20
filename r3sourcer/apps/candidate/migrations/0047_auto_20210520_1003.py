# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-05-20 10:03
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('candidate', '0046_auto_20210323_1645'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tagrel',
            name='tag',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tag_rels', to='core.Tag', verbose_name='Tag'),
        ),
    ]
