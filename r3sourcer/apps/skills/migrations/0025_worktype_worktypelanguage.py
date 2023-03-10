# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-01-26 15:10
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0142_auto_20210109_1110'),
        ('skills', '0024_remove_old_rate_range_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkType',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('name', models.CharField(max_length=127, verbose_name='Type of work')),
                ('skill_name', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='work_types', to='skills.SkillName', verbose_name='Skill Name')),
            ],
            options={
                'verbose_name': 'Type of work',
                'verbose_name_plural': 'Types of work',
            },
        ),
        migrations.CreateModel(
            name='WorkTypeLanguage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=127, verbose_name='Transalation')),
                ('language', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='work_types', to='core.Language', verbose_name='Language')),
                ('name', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='translations', to='skills.WorkType', verbose_name='Work Name')),
            ],
            options={
                'verbose_name': 'Work Transalation',
                'verbose_name_plural': 'Work Transalations',
            },
        ),
        migrations.AlterField(
            model_name='skillraterange',
            name='uom',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='skill_rate_ranges', to='core.UnitOfMeasurement', verbose_name='Unit of measurement'),
        ),
        migrations.AddField(
            model_name='skillraterange',
            name='worktype',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='skill_rate_ranges', to='skills.WorkType', verbose_name='WorkType'),
        ),
        migrations.AlterUniqueTogether(
            name='skillraterange',
            unique_together=set([('skill', 'worktype', 'uom')]),
        ),
        migrations.AlterUniqueTogether(
            name='worktypelanguage',
            unique_together=set([('name', 'language')]),
        ),
        migrations.AlterUniqueTogether(
            name='worktype',
            unique_together=set([('skill_name', 'name')]),
        ),
    ]
