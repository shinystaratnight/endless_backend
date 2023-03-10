# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-01-28 11:42
from __future__ import unicode_literals

import json
import os

from django.core.management import CommandError
from django.db import migrations


class Migration(migrations.Migration):

    def load_new_default_sms_templates_from_fixture(apps, schema_editor):
        DefaultEmailTemplate = apps.get_model("sms_interface", "DefaultSMSTemplate")
        Language = apps.get_model("core", "Language")
        email_templates = []
        try:
            basepath = os.path.dirname(__file__)
            filepath = os.path.abspath(os.path.join(
                basepath, "..", "fixtures", "default_sms_template.json")
            )
            with open(filepath, 'r') as json_file:
                data = json.load(json_file)
                for el in data:
                    if el['pk'] not in (54, 55, 56):
                        continue
                    template = el['fields']
                    lang = Language.objects.get(alpha_2=template['language'])
                    obj = DefaultEmailTemplate(
                        name=template['name'],
                        slug=template['slug'],
                        message_text_template=template['message_text_template'],
                        reply_timeout=template['reply_timeout'],
                        delivery_timeout=template['delivery_timeout'],
                        language=lang)
                    email_templates.append(obj)
            DefaultEmailTemplate.objects.bulk_create(email_templates)

        except Exception as e:
            raise CommandError(e)

    def remove_new_default_email_templates_from_fixture(apps, schema_editor):
        DefaultEmailTemplate = apps.get_model("sms_interface", "DefaultSMSTemplate")
        DefaultEmailTemplate.objects.filter(slug__contains="consent-sms-message").delete()

    def propagate_default_email_templates(apps, schema_editor):
        DefaultSMSTemplate = apps.get_model("sms_interface", "DefaultSMSTemplate")
        SMSTemplate = apps.get_model("sms_interface", "SMSTemplate")
        Company = apps.get_model("core", "Company")
        default_templates = DefaultSMSTemplate.objects.filter(slug__contains="consent-sms-message")
        sms_templates = []
        for company in Company.objects.all():
            if company.type != 'master':
                continue

            for template in default_templates:
                obj = SMSTemplate(
                    name=template.name,
                    slug=template.slug,
                    message_text_template=template.message_text_template,
                    reply_timeout=template.reply_timeout,
                    delivery_timeout=template.delivery_timeout,
                    company_id=company.id,
                    language=template.language)
                sms_templates.append(obj)
        SMSTemplate.objects.bulk_create(sms_templates)

    dependencies = [
        ('sms_interface', '0017_auto_20210104_1506'),
    ]

    operations = [
        # migrations.RunPython(load_new_default_sms_templates_from_fixture,
        #                      remove_new_default_email_templates_from_fixture),
        # migrations.RunPython(propagate_default_email_templates),
    ]
