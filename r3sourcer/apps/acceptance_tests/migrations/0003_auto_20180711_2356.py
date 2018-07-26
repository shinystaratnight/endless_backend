# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-07-11 13:56
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0057_workflow_node_relation_to_company'),
        ('acceptance_tests', '0002_acceptancetest_relations_and_score'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='acceptancetestworkflownode',
            name='workflow_node',
        ),
        migrations.AddField(
            model_name='acceptancetestworkflownode',
            name='company_workflow_node',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, related_name='acceptance_tests_workflow_nodes', to='core.CompanyWorkflowNode', verbose_name='Workflow Node'),
            preserve_default=False,
        ),
    ]