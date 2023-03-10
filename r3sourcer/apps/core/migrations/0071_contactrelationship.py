# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-11-12 08:14
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0070_contact_verification_token'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContactRelationship',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contact_relations', to='core.Company', verbose_name='Company')),
                ('contact', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contact_relations', to='core.Contact', verbose_name='Contact')),
            ],
            options={
                'verbose_name': 'Contact Relationship',
                'verbose_name_plural': 'Contact Relationships',
            },
        ),
    ]
