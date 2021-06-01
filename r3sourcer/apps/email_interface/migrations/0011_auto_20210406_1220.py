# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-04-06 12:20
from __future__ import unicode_literals

import json
import os

from django.core.management import CommandError
from django.db import migrations, models


class Migration(migrations.Migration):

    def load_new_default_email_templates_from_fixture(apps, schema_editor):
        DefaultEmailTemplate = apps.get_model("email_interface", "DefaultEmailTemplate")
        Language = apps.get_model("core", "Language")
        email_templates = []
        try:
            basepath = os.path.dirname(__file__)
            filepath = os.path.abspath(os.path.join(
                basepath, "..", "fixtures", "default_email_template.json")
            )
            with open(filepath, 'r') as json_file:
                data = json.load(json_file)
                for el in data:
                    try:
                        template = el['fields']
                        lang = Language.objects.get(alpha_2=template['language'])
                        existing_template = DefaultEmailTemplate.objects.get(slug=template['slug'], language=lang)
                        # update only consent templates
                        # might be removed after deployment
                        if existing_template.slug == 'consent-email-message':
                            existing_template.message_text_template = template['message_text_template']
                            existing_template.message_html_template = template['message_html_template']
                            existing_template.save()
                    except DefaultEmailTemplate.DoesNotExist:
                        obj = DefaultEmailTemplate(
                            name=template['name'],
                            slug=template['slug'],
                            subject_template=template['subject_template'],
                            message_text_template=template['message_text_template'],
                            message_html_template=template['message_html_template'],
                            reply_timeout=template['reply_timeout'],
                            delivery_timeout=template['delivery_timeout'],
                            language=lang)
                        email_templates.append(obj)
                    except Language.DoesNotExist:
                        continue
            if len(email_templates) > 0:
                DefaultEmailTemplate.objects.bulk_create(email_templates)

        except Exception as e:
            raise CommandError(e)

    dependencies = [
        ('email_interface', '0010_add_and_propagate_templates'),
    ]

    operations = [
        # migrations.RunPython(load_new_default_email_templates_from_fixture),
    ]
