# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2019-12-08 16:20
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0020_add_id_field_to_stripe_country'),
    ]

    operations = [
        migrations.AlterField(
            model_name='discount',
            name='created',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='payment',
            name='created',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='created',
            field=models.DateTimeField(),
        ),
    ]
