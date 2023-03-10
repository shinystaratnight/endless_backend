# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-03-06 18:36
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    def load_default_email_templates_from_fixture(apps, schema_editor):
        from django.core.management import call_command
        call_command("loaddata", "default_email_template")

    def delete_default_email_templates(apps, schema_editor):
        DefaultEmailTemplate = apps.get_model("email_interface", "DefaultEmailTemplate")
        DefaultEmailTemplate.objects.all().delete()

    def propagate_default_email_templates(apps, schema_editor):
        DefaultEmailTemplate = apps.get_model("email_interface", "DefaultEmailTemplate")
        EmailTemplate = apps.get_model("email_interface", "EmailTemplate")
        Company = apps.get_model("core", "Company")
        default_templates = DefaultEmailTemplate.objects.all()
        email_templates = []
        for company in Company.objects.all():
            if company.type != 'master':
                continue

            for template in default_templates:
                obj = EmailTemplate(
                    name=template.name,
                    slug=template.slug,
                    subject_template=template.subject_template,
                    message_text_template=template.message_text_template,
                    message_html_template=template.message_html_template,
                    reply_timeout=template.reply_timeout,
                    delivery_timeout=template.delivery_timeout,
                    company_id=company.id)
                email_templates.append(obj)
        EmailTemplate.objects.bulk_create(email_templates)

    dependencies = [
        ('core', '0097_auto_20200303_1432'),
        ('email_interface', '0005_auto_20191212_1443'),
    ]

    operations = [
        migrations.CreateModel(
            name='DefaultEmailTemplate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, default='', max_length=256, verbose_name='Name')),
                ('slug', models.SlugField()),
                ('message_text_template', models.TextField(default='', verbose_name='Text template')),
                ('subject_template', models.CharField(blank=True, default='', max_length=256, verbose_name='Subject template')),
                ('message_html_template', models.TextField(blank=True, default='', verbose_name='HTML template')),
                ('reply_timeout', models.IntegerField(default=10, help_text='Minutes', verbose_name='Reply timeout')),
                ('delivery_timeout', models.IntegerField(default=10, help_text='Minutes', verbose_name='Delivery timeout')),
            ],
            options={
                'verbose_name': 'Default Email Template',
                'verbose_name_plural': 'Default Email Templates',
                'ordering': ['name'],
            },
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='company',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='email_templates', to='core.Company', verbose_name='Master company'),
        ),
        migrations.AlterUniqueTogether(
            name='emailtemplate',
            unique_together=set([('company', 'name', 'slug')]),
        ),
        # migrations.RunPython(load_default_email_templates_from_fixture,
        #                      delete_default_email_templates),
        # migrations.RunPython(propagate_default_email_templates),
    ]
