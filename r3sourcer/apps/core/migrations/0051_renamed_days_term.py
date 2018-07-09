# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-07-09 08:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0050_reassign_client_terms_to_default'),
    ]

    operations = [
        migrations.AlterField(
            model_name='company',
            name='terms_of_payment',
            field=models.CharField(choices=[('prepaid', 'Prepaid'), ('on_delivery', 'Cash on delivery'), ('days', 'NET Days'), ('day_of_month', 'Day of the month'), ('days_eom', 'Days after EOM'), ('day_of_month_eom', 'Day of month after EOM')], default='on_delivery', max_length=20, verbose_name='Terms of Payment'),
        ),
    ]
