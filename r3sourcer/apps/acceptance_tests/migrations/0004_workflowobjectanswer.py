# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-07-13 13:53
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0060_removed_wf_company_node_unique'),
        ('acceptance_tests', '0003_auto_20180711_2356'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkflowObjectAnswer',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('answer_text', models.TextField(verbose_name='Text Answer')),
                ('score', models.PositiveSmallIntegerField(default=0, verbose_name='Answer Score')),
                ('acceptance_test_question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workflow_object_answers', to='acceptance_tests.AcceptanceTestQuestion', verbose_name='Acceptance Test Question')),
                ('answer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workflow_object_answers', to='acceptance_tests.AcceptanceTestAnswer', verbose_name='Acceptance Test Answer')),
                ('workflow_object', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workflow_object_answers', to='core.CompanyWorkflowNode', verbose_name='Workflow Object')),
            ],
            options={
                'verbose_name': 'Workflow Object Answer',
                'verbose_name_plural': 'Workflow Object Answers',
            },
        ),
    ]
