# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-05-16 07:15
from __future__ import unicode_literals

from django.db import migrations


def migrate_landline_and_fax(apps, schema_editor):
    CompanyAddress = apps.get_model("core", "CompanyAddress")

    for company_address in CompanyAddress.objects.all():
        company_address.phone_landline = company_address.address.phone_landline
        company_address.phone_fax = company_address.address.phone_fax
        company_address.save()


def reverse_landline_and_fax(apps, schema_editor):
    CompanyAddress = apps.get_model("core", "CompanyAddress")

    for company_address in CompanyAddress.objects.all():
        address = company_address.address
        address.phone_landline = company_address.phone_landline
        address.phone_fax = company_address.phone_fax
        address.save()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0028_added_landline_and_fax_company_address'),
    ]

    operations = [
        migrations.RunPython(migrate_landline_and_fax, reverse_landline_and_fax),
    ]
