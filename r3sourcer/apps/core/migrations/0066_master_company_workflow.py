# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-09-04 06:55
from __future__ import unicode_literals

from django.db import migrations


def migrate_master_company_workflow(apps, schema_editor):
    CompanyWorkflowNode = apps.get_model('core', 'CompanyWorkflowNode')
    Company = apps.get_model('core', 'Company')
    Workflow = apps.get_model('core', 'Workflow')
    WorkflowNode = apps.get_model('core', 'WorkflowNode')

    master_company_wf = Workflow.objects.filter(name='Master Company Workflow').first()

    if master_company_wf is not None:
        wf_nodes = WorkflowNode.objects.filter(workflow=master_company_wf)

        for company in Company.objects.filter(type='master'):
            for i, wf_node in enumerate(wf_nodes):
                CompanyWorkflowNode.objects.get_or_create(company=company, workflow_node=wf_node, order=i)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0065_changed_company_contact_rels'),
    ]

    operations = [
        migrations.RunPython(migrate_master_company_workflow, migrations.RunPython.noop)
    ]
