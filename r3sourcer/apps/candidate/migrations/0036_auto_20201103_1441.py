# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-11-03 14:41
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import uuid


def convert_tax_numbers(apps, _):
    TaxNumberType = apps.get_model('candidate', 'TaxNumberType')
    TaxNumber = apps.get_model('candidate', 'TaxNumber')
    CandidateContact = apps.get_model('candidate', 'CandidateContact')
    Country = apps.get_model('core', 'Country')
    candidate_contacts = CandidateContact.objects.all()
    for cc in candidate_contacts:
        country = cc.contact.address.country or Country.objects.get(name="Australia")
        tax_num_type, _ = TaxNumberType.objects.get_or_create(country=country, name='Tax File Number', max_length=9)
        tax_num = TaxNumber.objects.create(value=cc.tax_number, type=tax_num_type, default=True, candidate_contact=cc)




class Migration(migrations.Migration):

    dependencies = [
        ('core', '0129_auto_20201103_1441'),
        ('candidate', '0035_countryvisatyperelation'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaxNumber',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('value', models.CharField(max_length=64, verbose_name='Tax Number')),
                ('default', models.BooleanField()),
            ],
            options={
                'verbose_name_plural': 'Tax Numbers',
                'verbose_name': 'Tax Number',
            },
        ),
        migrations.CreateModel(
            name='TaxNumberType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64, verbose_name='Name')),
                ('max_length', models.IntegerField(verbose_name='Tax Number Length')),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='countries_set', to='core.Country', verbose_name='Country')),
            ],
            options={
                'verbose_name_plural': 'Tax Numbers Type',
                'verbose_name': 'Tax Number Type',
            },
        ),
        migrations.AddField(
            model_name='taxnumber',
            name='candidate_contact',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='candidate.CandidateContact', verbose_name='Candidate Contact'),
        ),
        migrations.AddField(
            model_name='taxnumber',
            name='type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='types', to='candidate.TaxNumberType', verbose_name='Type'),
        ),
        migrations.RunPython(convert_tax_numbers),
        migrations.RemoveField(
            model_name='candidatecontact',
            name='tax_file_number',
        ),
    ]
