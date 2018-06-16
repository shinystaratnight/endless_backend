# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-06-12 07:30
from __future__ import unicode_literals

from django.db import migrations
from r3sourcer.apps.core.models import Role


def migrate_candidate_roles(apps, schema_editor):
    RoleObj = apps.get_model("core", "Role")
    CandidateContact = apps.get_model("candidate", "CandidateContact")

    for candidate_contact in CandidateContact.objects.all():
        user = candidate_contact.contact.user
        if user and not user.role.filter(name=Role.ROLE_NAMES.candidate).exists():
            user.role.add(RoleObj.objects.create(name=Role.ROLE_NAMES.candidate))


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0034_add_roles'),
    ]

    operations = [
        migrations.RunPython(migrate_candidate_roles, migrations.RunPython.noop)
    ]