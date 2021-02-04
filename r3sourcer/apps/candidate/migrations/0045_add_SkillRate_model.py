# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-01-25 15:15
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    def move_rates_to_skillrate(apps, schema_editor):
        SkillRel = apps.get_model("candidate", "SkillRel")
        SkillRate = apps.get_model("candidate", "SkillRate")
        UnitOfMeasurement = apps.get_model("core", "UnitOfMeasurement")
        default_uom = UnitOfMeasurement.objects.get(default=True)

        for skill_rel in SkillRel.objects.all():
            if skill_rel.hourly_rate:
                SkillRate.objects.create(skill_rel=skill_rel,
                                         uom=default_uom,
                                         rate=skill_rel.hourly_rate)

    dependencies = [
        ('core', '0142_auto_20210109_1110'),
        ('candidate', '0044_auto_20210105_0705'),
        ('skills', '0025_worktype_worktypelanguage'),
    ]
    operations = [
        migrations.CreateModel(
            name='SkillRate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('rate', models.DecimalField(decimal_places=2, max_digits=8, verbose_name='Skill Rate')),
            ],
            options={
                'verbose_name': 'Skill rate',
                'verbose_name_plural': 'Skill rates',
            },
        ),
        migrations.AddField(
            model_name='skillrate',
            name='skill_rel',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='skill_rates', to='candidate.SkillRel', verbose_name='Candidate Skill'),
        ),
        migrations.AddField(
            model_name='skillrate',
            name='worktype',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='skill_rates', to='skills.WorkType', verbose_name='Type of work'),
        ),
        migrations.AddField(
            model_name='skillrate',
            name='uom',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.UnitOfMeasurement', verbose_name='Unit of measurement'),
        ),
        migrations.AlterUniqueTogether(
            name='skillrate',
            unique_together=set([('skill_rel', 'worktype', 'uom')]),
        ),
        migrations.RunPython(move_rates_to_skillrate),
        migrations.RemoveField(
            model_name='skillrel',
            name='hourly_rate',
        ),
    ]
