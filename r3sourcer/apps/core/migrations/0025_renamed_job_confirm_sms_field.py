# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-03-29 11:54
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_add_role'),
    ]

    operations = [
        migrations.RenameField(
            model_name='companycontact',
            old_name='receive_order_confirmation_sms',
            new_name='receive_job_confirmation_sms',
        ),
    ]
