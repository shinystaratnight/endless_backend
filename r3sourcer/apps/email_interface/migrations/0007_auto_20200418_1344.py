# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-04-18 13:44
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0111_auto_20200411_1214'),
        ('email_interface', '0006_auto_20200306_1836'),
    ]

    operations = [
        migrations.AddField(
            model_name='defaultemailtemplate',
            name='language',
            field=models.ForeignKey(default='en', on_delete=django.db.models.deletion.PROTECT, related_name='default_email_templates', to='core.Language', verbose_name='Language'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='emailtemplate',
            name='language',
            field=models.ForeignKey(default='en', on_delete=django.db.models.deletion.CASCADE, related_name='email_templates', to='core.Language', verbose_name='Template language'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='type',
            field=models.CharField(choices=[('email', 'Email')], default='email', max_length=8, verbose_name='Type'),
        ),
        migrations.AlterUniqueTogether(
            name='defaultemailtemplate',
            unique_together=set([('slug', 'language')]),
        ),
        migrations.AlterUniqueTogether(
            name='emailtemplate',
            unique_together=set([('company', 'name', 'slug', 'language')]),
        ),
    ]