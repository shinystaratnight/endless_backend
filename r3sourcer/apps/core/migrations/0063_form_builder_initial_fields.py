# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-08-08 09:39
from __future__ import unicode_literals

from django.db import migrations


def fill_form_builder_fields(apps, schema_editor):
    FormBuilder = apps.get_model("core", "FormBuilder")

    form_builders = FormBuilder.objects.filter(content_type__model='candidatecontact')
    for form_builder in form_builders:
        form_builder.fields = [
            'contact__title', 'contact__first_name', 'contact__last_name', 'contact__email', 'contact__phone_mobile',
            'contact__gender', 'contact__birthday', 'contact__picture', 'contact__address', 'transportation_to_work',
            'height', 'weight', 'residency', 'nationality', 'tax_file_number', 'bank_account', 'superannuation_fund'
        ]
        form_builder.save()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0062_company_sms_enabled'),
    ]

    operations = [
        migrations.RunPython(fill_form_builder_fields, migrations.RunPython.noop)
    ]
