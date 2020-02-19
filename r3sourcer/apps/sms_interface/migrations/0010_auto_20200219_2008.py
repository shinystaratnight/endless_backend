# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-02-19 20:08
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    def load_default_sms_templates_from_fixture(apps, schema_editor):
        from django.core.management import call_command
        call_command("loaddata", "default_sms_template")

    def delete_default_sms_templates(apps, schema_editor):
        DefaultSMSTemplate = apps.get_model("sms_interface", "DefaultSMSTemplate")
        DefaultSMSTemplate.objects.all().delete()

    dependencies = [
        ('sms_interface', '0009_change_sms_defaults'),
    ]

    operations = [
        migrations.CreateModel(
            name='DefaultSMSTemplate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, default='', max_length=256, verbose_name='Name')),
                ('slug', models.SlugField()),
                ('message_text_template', models.TextField(default='', verbose_name='Text template')),
                ('reply_timeout', models.IntegerField(default=10, help_text='Minutes', verbose_name='Reply timeout')),
                ('delivery_timeout', models.IntegerField(default=10, help_text='Minutes', verbose_name='Delivery timeout')),
            ],
            options={
                'verbose_name': 'Default SMS Template',
                'verbose_name_plural': 'Default SMS Templates',
                'ordering': ['name'],
            },
        ),
        migrations.AlterField(
            model_name='smstemplate',
            name='company',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sms_templates', to='core.Company', verbose_name='Master company'),
        ),
        migrations.RunPython(load_default_sms_templates_from_fixture,
                             delete_default_sms_templates),
    ]
