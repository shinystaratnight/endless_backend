# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-06-21 09:17
from __future__ import unicode_literals

from django.db import migrations


def migrate_default_skill_rate(apps, schema_editor):
    SkillRel = apps.get_model("candidate", "SkillRel")

    for skill_rel in SkillRel.objects.all():
        default_base_rate = skill_rel.candidate_skill_rates.filter(hourly_rate__default_rate=True).first()
        if not default_base_rate:
            default_base_rate = skill_rel.candidate_skill_rates.filter(
                hourly_rate__isnull=False
            ).order_by('hourly_rate__hourly_rate').first()

        if not default_base_rate:
            continue

        default_rate = default_base_rate.hourly_rate.hourly_rate
        skill_rel.hourly_rate = default_rate
        skill_rel.save()


class Migration(migrations.Migration):

    dependencies = [
        ('candidate', '0007_skillrel_hourly_rate'),
    ]

    operations = [
        migrations.RunPython(migrate_default_skill_rate, migrations.RunPython.noop)
    ]
