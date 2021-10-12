# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-10-01 16:09
from __future__ import unicode_literals

from django.db import migrations, models
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0148_auto_20211001_1150'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='new_email',
            field=models.EmailField(blank=True, max_length=255, null=True, verbose_name='New E-mail'),
        ),
        migrations.AlterField(
            model_name='contact',
            name='new_phone_mobile',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, null=True, region=None, verbose_name='New Mobile Phone'),
        ),
    ]