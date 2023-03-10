# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-02-26 14:31
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0143_merge_20210212_0605'),
        ('skills', '0026_auto_20210224_1615'),
    ]

    operations = [
        migrations.AddField(
            model_name='worktype',
            name='skill',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='work_types', to='skills.Skill', verbose_name='Skill Name'),
        ),
        migrations.AlterField(
            model_name='worktype',
            name='skill_name',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='work_types', to='skills.SkillName', verbose_name='Skill Name'),
        ),
        migrations.AlterUniqueTogether(
            name='worktype',
            unique_together=set([('skill_name', 'skill', 'uom', 'name')]),
        ),
    ]
