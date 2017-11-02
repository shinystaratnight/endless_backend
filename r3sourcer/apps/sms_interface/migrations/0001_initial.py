# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-11-02 16:44
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0002_auto_20171102_1757'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='PhoneNumber',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('sid', models.CharField(editable=False, help_text='Number ID', max_length=254, unique=True, verbose_name='SID')),
                ('phone_number', models.CharField(max_length=32, verbose_name='Phone')),
                ('friendly_name', models.CharField(default='', editable=False, max_length=512, verbose_name='Friendly name')),
                ('sms_enabled', models.BooleanField(default=True, verbose_name='SMS enabled')),
                ('mms_enabled', models.BooleanField(default=True, verbose_name='MMS enabled')),
                ('voice_enabled', models.BooleanField(default=True, verbose_name='VOICE enabled')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='phone_numbers', to='core.Company', verbose_name='Company')),
            ],
            options={
                'verbose_name': 'Phone number',
                'verbose_name_plural': 'Phone numbers',
            },
        ),
        migrations.CreateModel(
            name='SMSMessage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('reply_timeout', models.IntegerField(default=4, help_text='Minutes', verbose_name='Reply timeout')),
                ('delivery_timeout', models.IntegerField(default=4, help_text='Minutes', verbose_name='Delivery timeout')),
                ('sid', models.CharField(editable=False, help_text='Twillio Message ID', max_length=254, verbose_name='SID')),
                ('status', models.CharField(blank=True, choices=[('ACCEPTED', 'Accepted'), ('SENT', 'Sent'), ('QUEUED', 'Queued'), ('SENDING', 'Sending'), ('SENT', 'Sent'), ('FAILED', 'Failed'), ('DELIVERED', 'Delivered'), ('UNDELIVERED', 'Undelivered'), ('RECEIVED', 'Received')], max_length=25, null=True, verbose_name='Status')),
                ('type', models.CharField(blank=True, choices=[('SENT', 'SMS sent'), ('RECEIVED', 'SMS received')], default='SENT', max_length=15, verbose_name='Type')),
                ('text', models.TextField(blank=True, null=True, verbose_name='Text message')),
                ('trash', models.BooleanField(default=False, verbose_name='Trash')),
                ('related_object_id', models.UUIDField(blank=True, null=True)),
                ('check_delivered', models.BooleanField(default=False, verbose_name='Check delivered status after timeout')),
                ('check_reply', models.BooleanField(default=False, verbose_name='Check reply status after timeout')),
                ('from_number', models.CharField(blank=True, default='', max_length=25, null=True, verbose_name='From number')),
                ('to_number', models.CharField(blank=True, max_length=25, null=True, verbose_name='To number')),
                ('sent_at', models.DateTimeField(blank=True, null=True, verbose_name='Sent at')),
                ('check_delivery_at', models.DateTimeField(blank=True, null=True, verbose_name='Check delivery date')),
                ('check_reply_at', models.DateTimeField(blank=True, null=True, verbose_name='Check reply at')),
                ('is_fetched', models.BooleanField(default=False, verbose_name='SMS fetched')),
                ('error_code', models.TextField(blank=True, default='', null=True, verbose_name='Error code')),
                ('error_message', models.TextField(blank=True, default='', null=True, verbose_name='Error message')),
                ('is_fake', models.BooleanField(default=False, verbose_name='Fake sms')),
                ('late_reply', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sent_sms_messages', to='sms_interface.SMSMessage', verbose_name='Late reply')),
                ('related_content_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
                ('reply_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='replyto', to='sms_interface.SMSMessage', verbose_name='Reply to')),
            ],
            options={
                'verbose_name': 'SMS message',
                'verbose_name_plural': 'SMS messages',
                'ordering': ['-sent_at'],
            },
        ),
        migrations.CreateModel(
            name='SMSRelatedObject',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('object_id', models.UUIDField()),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
                ('sms', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='related_objects', to='sms_interface.SMSMessage', verbose_name='SMS message')),
            ],
            options={
                'verbose_name': 'SMS related object',
                'verbose_name_plural': 'SMS related objects',
            },
        ),
        migrations.CreateModel(
            name='SMSTemplate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('name', models.CharField(db_index=True, default='', max_length=256, verbose_name='Name')),
                ('slug', models.SlugField()),
                ('message_text_template', models.TextField(blank=True, default='', verbose_name='Text template')),
                ('reply_timeout', models.IntegerField(default=10, help_text='Minutes', verbose_name='Reply timeout')),
                ('delivery_timeout', models.IntegerField(default=10, help_text='Minutes', verbose_name='Delivery timeout')),
                ('type', models.CharField(choices=[('sms', 'SMS')], max_length=8, verbose_name='Type')),
                ('company', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Company', verbose_name='Master company')),
            ],
            options={
                'verbose_name': 'SMS Template',
                'verbose_name_plural': 'SMS Templates',
                'ordering': ['name'],
            },
        ),
    ]
