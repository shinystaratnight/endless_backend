# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-01-18 14:27
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('email_interface', '0008_load_new_default_email_templates'),
        ('billing', '0022_auto_20191211_1621'),
    ]

    operations = [
        migrations.CreateModel(
            name='SMSBalanceLimits',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('low_balance_limit', models.PositiveIntegerField(default=20)),
                ('email_template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='email_interface.DefaultEmailTemplate')),
            ],
        ),
    ]
