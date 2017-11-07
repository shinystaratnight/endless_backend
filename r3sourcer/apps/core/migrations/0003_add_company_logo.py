# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-11-02 15:57
from __future__ import unicode_literals

import autoslug.fields
import cities_light.abstract_models
from django.conf import settings
import django.contrib.postgres.fields.jsonb
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import djmoney.models.fields
import easy_thumbnails.fields
import mptt.fields
import phonenumber_field.modelfields
import r3sourcer.apps.core.mixins
import r3sourcer.apps.core.models.core
import r3sourcer.apps.core.utils.validators
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_auto_20171102_1757'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='logo',
            field=easy_thumbnails.fields.ThumbnailerImageField(blank=True, default='/var/www/media/company_pictures/default_picture.jpg', upload_to='company_pictures'),
        ),
    ]
