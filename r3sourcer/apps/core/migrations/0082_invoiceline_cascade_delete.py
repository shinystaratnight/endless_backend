# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2019-04-09 19:15
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0081_added_timezone_to_country'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoiceline',
            name='invoice',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invoice_lines', to='core.Invoice', verbose_name='Invoice'),
        ),
    ]
