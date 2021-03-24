# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-03-24 14:34
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    def hourly_worktypes_add(apps, schema_editor):
        SkillName = apps.get_model("skills", "SkillName")
        WorkType = apps.get_model("skills", "WorkType")
        UnitOfMeasurement = apps.get_model("core", "UnitOfMeasurement")
        default_uom = UnitOfMeasurement.objects.get(default=True)

        for skill_name in SkillName.objects.all():
            if not WorkType.objects.filter(skill_name=skill_name,
                                           name='Hourly work').exists():
                WorkType.objects.create(skill_name=skill_name,
                                        uom=default_uom,
                                        name='Hourly work'
                                        )


    dependencies = [
        ('skills', '0027_auto_20210226_1431'),
    ]

    operations = [
        migrations.RunPython(hourly_worktypes_add),
    ]
