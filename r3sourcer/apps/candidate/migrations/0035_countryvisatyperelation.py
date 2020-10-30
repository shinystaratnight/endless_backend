# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-10-29 12:33
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    def migrate_visa_types(self, _):
        VisaType = self.get_model('candidate', 'VisaType')
        CountryVisaTypeRelation = self.get_model('candidate', 'CountryVisaTypeRelation')
        Country = self.get_model('core', 'Country')
        vts = VisaType.objects.all()
        aus = Country.objects.get(name="Australia")
        for obj in vts:
            cvt = CountryVisaTypeRelation.objects.create(country=aus, visa_type=obj)
            cvt.save()

    dependencies = [
        ('core', '0128_auto_20201019_1231'),
        ('candidate', '0034_auto_20200611_1257'),
    ]

    operations = [
        migrations.RunPython(migrate_visa_types, migrations.RunPython.noop),
        migrations.CreateModel(
            name='CountryVisaTypeRelation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='countries', to='core.Country', verbose_name='Country')),
                ('visa_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='visa_types', to='candidate.VisaType', verbose_name='Visa Type')),
            ],
            options={
                'verbose_name': 'Country Visa Type',
                'verbose_name_plural': 'Country Visa Types',
            },
        ),
    ]
