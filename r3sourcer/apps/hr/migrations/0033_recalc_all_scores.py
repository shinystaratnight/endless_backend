# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-10-16 07:35
from __future__ import unicode_literals

from django.db import migrations, transaction


def batch(iterable, n):
    size = iterable.count()
    for ndx in range(0, size, n):
        yield iterable[ndx:min(ndx + n, size)]


def recalc_scores(apps, schema_editor):
    from r3sourcer.apps.hr.models import CandidateScore

    SkillRel = apps.get_model('candidate', 'SkillRel')

    SkillRel.objects.filter(score__gt=5).update(score=5)

    for batch_score in batch(CandidateScore.objects.all(), 50):
        with transaction.atomic():
            for candidate_scores in batch_score:
                candidate_scores.recalc_scores()


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0032_candidatescore_skill_score'),
        ('candidate', '0020_removed_legacy_superannuation_fields'),
    ]

    operations = [
        migrations.RunPython(recalc_scores, migrations.RunPython.noop)
    ]