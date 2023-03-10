# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-10-19 12:31
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0127_vat_stripe_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='FormLanguage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=127, verbose_name='Title transalation')),
                ('short_description', models.CharField(max_length=127, verbose_name='Description transalation')),
                ('save_button_text', models.CharField(max_length=127, verbose_name='Save transalation')),
                ('submit_message', models.CharField(max_length=127, verbose_name='Submit transalation')),
                ('form', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='translations', to='core.Form', verbose_name='Translation Fields')),
                ('language', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='form_trans', to='core.Language', verbose_name='From fields language')),
            ],
            options={
                'verbose_name_plural': 'Form Languages',
                'verbose_name': 'Form Language',
            },
        ),
        migrations.AlterUniqueTogether(
            name='formlanguage',
            unique_together=set([('form', 'language')]),
        ),
    ]
