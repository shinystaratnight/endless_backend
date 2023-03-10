# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-01-04 14:32
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    def load_default_sms_templates_from_fixture(apps, schema_editor):
        from django.core.management import call_command
        call_command("loaddata", "default_sms_template")

    def delete_default_sms_templates(apps, schema_editor):
        DefaultSMSTemplate = apps.get_model("sms_interface", "DefaultSMSTemplate")
        DefaultSMSTemplate.objects.all().delete()

    def load_sms_templates_from_fixture(apps, schema_editor):
        from django.core.management import call_command
        call_command("loaddata", "sms_template")

    def delete_sms_templates(apps, schema_editor):
        DefaultSMSTemplate = apps.get_model("sms_interface", "SMSTemplate")
        DefaultSMSTemplate.objects.all().delete()


    dependencies = [
        ('sms_interface', '0016_auto_20200515_1812'),
    ]

    operations = [
        # migrations.RunPython(load_default_sms_templates_from_fixture,
        #                      delete_default_sms_templates),
        # migrations.RunPython(load_sms_templates_from_fixture,
        #                      delete_sms_templates),
    ]
