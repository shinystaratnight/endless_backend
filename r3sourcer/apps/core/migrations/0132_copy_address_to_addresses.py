# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-12-03 17:33 update
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    def make_many_addresses(apps, schema_editor):
        """
            Adds the Author object in Book.author to the
            many-to-many relationship in Book.authors
        """
        Contact = apps.get_model('core', 'Contact')
        ContactAddress = apps.get_model('core', 'ContactAddress')

        for contact in Contact.objects.all():
            if contact.address:
                contact_address = ContactAddress(contact=contact, address=contact.address)
                contact_address.save()


    dependencies = [
        ('core', '0131_auto_20201203_1232'),
    ]

    operations = [
        migrations.RunPython(make_many_addresses),
    ]
