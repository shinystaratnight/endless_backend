# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-04-16 18:07
from __future__ import unicode_literals
from django.conf import settings

from django.db import migrations


def propagate_default_master_company_languages(apps, schema_editor):
    Company = apps.get_model("core", "Company")
    CompanyLanguage = apps.get_model("core", "CompanyLanguage")
    CandidateContactLanguage = apps.get_model("candidate", "CandidateContactLanguage")
    for company in Company.objects.filter(type='master').all():
        company_language = company.languages.filter(default=True).first()
        if not company_language:
            company_language = company.languages.filter(language_id=settings.DEFAULT_LANGUAGE).first()
        if not company_language:
            company_language = CompanyLanguage(
                company=company,
                language_id=settings.DEFAULT_LANGUAGE,
                default=True
            )
        else:
            company_language.default = True
        company_language.save()
        for can_rel in company.candidate_rels.all():
            candidate_contact = can_rel.candidate_contact
            candidate_language = candidate_contact.languages.filter(default=True).first()
            if not candidate_language:
                candidate_language = candidate_contact.languages.filter(
                    language_id=company_language.language_id,
                ).first()
            if not candidate_language:
                candidate_language = CandidateContactLanguage(
                    candidate_contact=candidate_contact,
                    language_id=company_language.language_id,
                    default=True
                )
            else:
                candidate_language.default = True
            candidate_language.save()


class Migration(migrations.Migration):

    dependencies = [
        ('candidate', '0031_auto_20200321_1817'),
    ]

    operations = [
        migrations.RunPython(propagate_default_master_company_languages),
    ]
