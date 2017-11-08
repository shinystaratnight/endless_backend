# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-11-07 17:23
from __future__ import unicode_literals

from django.db import migrations, models
import easy_thumbnails.fields


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0008_alter_user_username_max_length'),
        ('core', '0002_auto_20171102_1757'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='groups',
            field=models.ManyToManyField(related_name='companies', to='auth.Group'),
        ),
        migrations.AlterField(
            model_name='contact',
            name='picture',
            field=easy_thumbnails.fields.ThumbnailerImageField(blank=True, default='/Users/fedotkin/PycharmProjects/endless_project/var/www/media/contact_pictures/default_picture.jpg', max_length=255, upload_to='contact_pictures'),
        ),
    ]
