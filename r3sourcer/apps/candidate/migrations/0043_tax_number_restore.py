# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-12-15 04:45
from __future__ import unicode_literals

import json

import os
from django.core.management import CommandError
from django.db import migrations


class Migration(migrations.Migration):

    def load_tax_numbers(apps, schema_editor):
        Formality = apps.get_model("candidate", "Formality")
        Country = apps.get_model("core", "Country")
        tax_numbers = []
        try:
            basepath = os.path.dirname(__file__)
            filepath = os.path.abspath(os.path.join(
                basepath, "..", "fixtures", "tax_file_numbers.json")
            )
            with open(filepath, 'r') as json_file:
                data = json.load(json_file)
                for el in data:
                    template = el['fields']
                    country = Country.objects.get(code2=template['country'])
                    obj = Formality(
                        candidate_contact_id=template['candidate_contact'],
                        tax_number=template['tax_number'],
                        country=country)
                    tax_numbers.append(obj)
            Formality.objects.bulk_create(tax_numbers)

        except Exception as e:
            raise CommandError(e)

    dependencies = [
        ('candidate', '0042_formality'),
    ]

    operations = [
        migrations.RunPython(load_tax_numbers),
    ]