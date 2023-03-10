# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-01-11 10:24
from __future__ import unicode_literals

from django.db import migrations


def create_rules(apps, schema_editor):
    Company = apps.get_model("core", "Company")
    InvoiceRule = apps.get_model("core", "InvoiceRule")

    companies = Company.objects.all()

    for company in companies:
        if not company.invoice_rules.all():
            InvoiceRule.objects.create(company=company)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_add_workflownode_endpoint'),
    ]

    operations = [
        migrations.RunPython(create_rules)
    ]
