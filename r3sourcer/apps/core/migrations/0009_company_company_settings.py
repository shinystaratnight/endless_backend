# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-11-08 13:18
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import easy_thumbnails.fields


class Migration(migrations.Migration):

    dependencies = [
        ('company_settings', '0001_initial'),
        ('core', '0008_auto_20171128_0136'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='picture',
            field=easy_thumbnails.fields.ThumbnailerImageField(blank=True, default='/Users/fedotkin/PycharmProjects/endless_project/var/www/media/contact_pictures/default_picture.jpg', max_length=255, upload_to='contact_pictures'),
        ),
        migrations.AddField(
            model_name='company',
            name='company_settings',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                       to='company_settings.CompanySettings'),
        ),
    ]
