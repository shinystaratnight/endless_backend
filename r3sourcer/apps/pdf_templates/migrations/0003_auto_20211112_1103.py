# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-11-12 11:03
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pdf_templates', '0002_load_pdf_templates'),
    ]

    def load_default_pdf_templates_from_fixture(apps, schema_editor):

        from django.core.management import call_command

        call_command("loaddata", "default_pdf_templates")


    def load_pdf_templates_from_fixture(apps, schema_editor):

        from django.core.management import call_command

        call_command("loaddata", "pdf_templates")


    operations = [

        migrations.RunPython(load_default_pdf_templates_from_fixture),

        migrations.RunPython(load_pdf_templates_from_fixture),

    ]
