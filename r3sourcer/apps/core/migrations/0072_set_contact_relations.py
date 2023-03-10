# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-11-12 08:15
from __future__ import unicode_literals

from django.db import migrations


def migrate_contact_relations(apps, schema_editor):
    Contact = apps.get_model('core', 'Contact')
    ContactRelationship = apps.get_model('core', 'ContactRelationship')

    for contact in Contact.objects.all():
        if hasattr(contact, 'candidate_contacts'):
            companies = [
                candidate_rel.master_company
                for candidate_rel in contact.candidate_contacts.candidate_rels.filter(active=True)
            ]
        else:
            companies = []

        for company_contact in contact.company_contact.filter(relationships__active=True):
            companies.extend([
                company_rel.company
                for company_rel in company_contact.relationships.filter(active=True)
            ])

        master_companies = []
        for company in companies:
            if company.type == 'master':
                master_companies.append(company)
            else:
                master_companies.extend([
                    company_rel.master_company for company_rel in company.regular_companies.all()
                ])

        rels = [
            ContactRelationship(contact=contact, company=company) for company in set(master_companies)
        ]
        ContactRelationship.objects.bulk_create(rels)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0071_contactrelationship'),
    ]

    operations = [
        migrations.RunPython(migrate_contact_relations, migrations.RunPython.noop)
    ]
