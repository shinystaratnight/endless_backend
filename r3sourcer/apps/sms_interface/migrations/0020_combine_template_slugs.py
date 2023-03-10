# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-05-06 09:44
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    def combine_template_slugs(apps, schema_editor):
        DefaultSMSTemplate = apps.get_model("sms_interface", "DefaultSMSTemplate")
        SMSTemplate = apps.get_model("sms_interface", "SMSTemplate")

        for template in DefaultSMSTemplate.objects.filter(slug="consent-sms-message"):
            template.slug = "consent-message"
            template.name = "Consent message"
            template.save()

        for template in SMSTemplate.objects.filter(slug="consent-sms-message"):
            template.slug = "consent-message"
            template.name = "Consent message"
            template.save()

        for template in DefaultSMSTemplate.objects.filter(slug="login-sms-token"):
            template.slug = "login-token"
            template.name = "Login Token"
            template.save()

        for template in SMSTemplate.objects.filter(slug="login-sms-token"):
            template.slug = "login-token"
            template.name = "Login Token"
            template.save()

    dependencies = [
        ('sms_interface', '0019_load_new_sms_templates'),
    ]

    operations = [
        migrations.RunPython(combine_template_slugs),
    ]
