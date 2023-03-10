# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-03-26 13:40
from __future__ import unicode_literals

from django.db import migrations, models


def delete_auth_data(apps, schema_editor):
    MYOBAuthData = apps.get_model("myob", "MYOBAuthData")
    MYOBAuthData.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('myob', '0007_auth_data_delete_uniqueness'),
    ]

    operations = [
        migrations.AlterField(
            model_name='myobauthdata',
            name='myob_user_username',
            field=models.CharField(max_length=512, unique=True, verbose_name='User Username'),
        ),
        migrations.RunPython(delete_auth_data, migrations.RunPython.noop)
    ]
