# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-11-10 15:54
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('email_interface', '0013_combine_template_slugs'),
    ]

    def load_default_email_templates_from_fixture(apps, schema_editor):
        from django.core.management import call_command
        call_command("loaddata", "default_email_templates")

    def load_email_templates_from_fixture(apps, schema_editor):
        from django.core.management import call_command
        call_command("loaddata", "email_templates")

    operations = [
        migrations.RunPython(load_default_email_templates_from_fixture),
        migrations.RunPython(load_email_templates_from_fixture),
    ]