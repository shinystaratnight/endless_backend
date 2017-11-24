# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-11-24 12:03
from __future__ import unicode_literals

from django.db import migrations, models


def delete_duplicates(apps, schema_editor):
    SkillBaseRate = apps.get_model("skills", "SkillBaseRate")
    rate_list = SkillBaseRate.objects.values('skill', 'hourly_rate').annotate(models.Count('pk'))

    for rate in rate_list:
        if rate['pk__count'] > 1:
            rates_to_delete = SkillBaseRate.objects.filter(hourly_rate=rate['hourly_rate'],
                                                           skill=rate['skill'])[:rate['pk__count'] - 1]
            pk_list = [x.pk for x in rates_to_delete]
            SkillBaseRate.objects.filter(pk__in=pk_list).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('skills', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(delete_duplicates),
    ]
