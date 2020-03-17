# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-03-03 14:32
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0096_invoice_sync_status'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='checkboxformfield',
            managers=[
                ('inheritance_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='dateformfield',
            managers=[
                ('inheritance_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='fileformfield',
            managers=[
                ('inheritance_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='imageformfield',
            managers=[
                ('inheritance_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='modelformfield',
            managers=[
                ('inheritance_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='numberformfield',
            managers=[
                ('inheritance_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='radiobuttonsformfield',
            managers=[
                ('inheritance_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='relatedformfield',
            managers=[
                ('inheritance_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='selectformfield',
            managers=[
                ('inheritance_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='textareaformfield',
            managers=[
                ('inheritance_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='textformfield',
            managers=[
                ('inheritance_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterField(
            model_name='extranetnavigation',
            name='level',
            field=models.PositiveIntegerField(editable=False),
        ),
        migrations.AlterField(
            model_name='extranetnavigation',
            name='lft',
            field=models.PositiveIntegerField(editable=False),
        ),
        migrations.AlterField(
            model_name='extranetnavigation',
            name='rght',
            field=models.PositiveIntegerField(editable=False),
        ),
        migrations.AlterField(
            model_name='tag',
            name='level',
            field=models.PositiveIntegerField(editable=False),
        ),
        migrations.AlterField(
            model_name='tag',
            name='lft',
            field=models.PositiveIntegerField(editable=False),
        ),
        migrations.AlterField(
            model_name='tag',
            name='rght',
            field=models.PositiveIntegerField(editable=False),
        ),
    ]