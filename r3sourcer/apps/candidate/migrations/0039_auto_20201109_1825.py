# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-11-09 18:25
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0129_auto_20201103_1441'),
        ('candidate', '0038_auto_20201106_1453'),
    ]

    operations = [
        migrations.CreateModel(
            name='PersonalID',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('value', models.CharField(max_length=64, verbose_name='Tax Number')),
                ('default', models.BooleanField(default=False)),
                ('candidate_contact', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='candidate.CandidateContact', verbose_name='Candidate Contact')),
            ],
            options={
                'verbose_name_plural': 'Personal IDs',
                'verbose_name': 'Personal ID',
            },
        ),
        migrations.CreateModel(
            name='PersonalIDType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64, verbose_name='Name')),
                ('regex_validation_pattern', models.CharField(max_length=64, verbose_name='Tax Number Regex Validation Pattern')),
                ('country', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='core.Country', verbose_name='Country')),
            ],
            options={
                'verbose_name_plural': 'Personal ID Type',
                'verbose_name': 'Personal ID Type',
            },
        ),
        migrations.AddField(
            model_name='personalid',
            name='type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='id_types', to='candidate.PersonalIDType', verbose_name='ID Type'),
        ),
    ]
