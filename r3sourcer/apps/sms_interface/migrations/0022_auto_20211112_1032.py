# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-11-12 10:32
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sms_interface', '0021_add_carrier_list_templates'),
    ]

    def load_default_sms_templates_from_fixture(apps, schema_editor):
        from django.core.management import call_command
        call_command("loaddata", "default_sms_templates")

    def load_sms_templates_from_fixture(apps, schema_editor):
        from django.core.management import call_command
        call_command("loaddata", "sms_templates")

    operations = [
        migrations.RunPython(load_default_sms_templates_from_fixture),
        migrations.RunPython(load_sms_templates_from_fixture),
    ]
