# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-02-21 08:06
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('login', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tokenlogin',
            name='redirect_to',
            field=models.CharField(default='/', max_length=127, verbose_name='Redirect Url'),
        ),
    ]
