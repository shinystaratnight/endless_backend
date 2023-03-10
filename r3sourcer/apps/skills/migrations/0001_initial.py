# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-11-02 17:33
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='EmploymentClassification',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('name', models.CharField(max_length=255, verbose_name='Name')),
            ],
            options={
                'verbose_name_plural': 'Employment Classifications',
                'verbose_name': 'Employment Classification',
            },
        ),
        migrations.CreateModel(
            name='Skill',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('name', models.CharField(max_length=63, verbose_name='Skill Name')),
                ('carrier_list_reserve', models.PositiveSmallIntegerField(default=0, verbose_name='Carrier List Reserve')),
                ('short_name', models.CharField(blank=True, help_text='Abbreviation, for use by staff reports and dashboards', max_length=15, verbose_name='Short Name')),
                ('active', models.BooleanField(default=True, verbose_name='Active')),
                ('employment_classification', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='skills', to='skills.EmploymentClassification', verbose_name='Employment Classification')),
            ],
            options={
                'verbose_name_plural': 'Skills',
                'verbose_name': 'Skill',
            },
        ),
        migrations.CreateModel(
            name='SkillBaseRate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('hourly_rate', models.DecimalField(decimal_places=2, default=0.0, max_digits=8, verbose_name='Hourly Rate')),
                ('skill', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='skill_rate_defaults', to='skills.Skill', verbose_name='Skill')),
            ],
            options={
                'verbose_name_plural': 'Skill Base Rates',
                'ordering': ('hourly_rate',),
                'verbose_name': 'Skill Base Rate',
            },
        ),
    ]
