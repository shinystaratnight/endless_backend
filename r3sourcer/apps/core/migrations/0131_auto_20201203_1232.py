# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-12-03 12:32 update
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0130_country_has_separate_personal_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContactAddress',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('address', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contact_address', to='core.Address', verbose_name='Address')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PersonalID',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('value', models.CharField(max_length=64, verbose_name='Value')),
                ('contact_address', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='core.ContactAddress', verbose_name='Contact address')),
            ],
            options={
                'verbose_name': 'Personal ID',
                'verbose_name_plural': 'Personal IDs',
            },
        ),
        migrations.CreateModel(
            name='TaxNumber',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('value', models.CharField(max_length=64, verbose_name='Value')),
                ('contact_address', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='core.ContactAddress', verbose_name='Contact address')),
            ],
            options={
                'verbose_name': 'Tax Number',
                'verbose_name_plural': 'Tax Numbers',
            },
        ),
        migrations.RemoveField(
            model_name='country',
            name='has_separate_personal_id',
        ),
        migrations.AddField(
            model_name='country',
            name='display_personal_id',
            field=models.BooleanField(default=False, verbose_name='Display Personal ID'),
        ),
        migrations.AddField(
            model_name='country',
            name='display_tax_number',
            field=models.BooleanField(default=False, verbose_name='Display Tax Number'),
        ),
        migrations.AddField(
            model_name='country',
            name='personal_id_regex_validation_pattern',
            field=models.CharField(blank=True, max_length=64, verbose_name='Personal ID Regex Validation Pattern'),
        ),
        migrations.AddField(
            model_name='country',
            name='personal_id_type',
            field=models.CharField(blank=True, max_length=64, verbose_name='Tax number type'),
        ),
        migrations.AddField(
            model_name='country',
            name='tax_number_regex_validation_pattern',
            field=models.CharField(blank=True, max_length=64, verbose_name='Tax Number Regex Validation Pattern'),
        ),
        migrations.AddField(
            model_name='country',
            name='tax_number_type',
            field=models.CharField(blank=True, max_length=64, verbose_name='Tax number type'),
        ),
        migrations.AlterField(
            model_name='contact',
            name='address',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Address', verbose_name='Address'),
        ),
        migrations.AddField(
            model_name='contactaddress',
            name='contact',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contact_address', to='core.Contact', verbose_name='Contact'),
        ),
        migrations.AddField(
            model_name='contact',
            name='addresses',
            field=models.ManyToManyField(blank=True, related_name='contacts', through='core.ContactAddress', to='core.Address', verbose_name='Addresses'),
        ),
    ]
