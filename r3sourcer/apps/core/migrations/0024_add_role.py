# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-03-23 11:03
from __future__ import unicode_literals

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_invoice_approved'),
    ]

    operations = [
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('name', models.CharField(choices=[('candidate', 'Candidate'), ('manager', 'Manager'), ('client', 'Client')], max_length=255)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.ManyToManyField(to='core.Role'),
        ),
    ]
