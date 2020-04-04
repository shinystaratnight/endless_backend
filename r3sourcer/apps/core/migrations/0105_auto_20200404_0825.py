# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-04-04 08:25
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0104_company_default_phone_prefix'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompanyLanguage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('default', models.BooleanField(default=False)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='languages', to='core.Company', verbose_name='Company')),
                ('language', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='company_languages', to='core.Language', verbose_name='Language')),
            ],
            options={
                'verbose_name': 'Company language',
                'verbose_name_plural': 'Company languages',
            },
        ),
        migrations.AlterField(
            model_name='companyrel',
            name='manager',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='company_accounts', to='core.CompanyContact', verbose_name='Primary Contact'),
        ),
        migrations.AlterUniqueTogether(
            name='companylanguage',
            unique_together=set([('company', 'language')]),
        ),
    ]
