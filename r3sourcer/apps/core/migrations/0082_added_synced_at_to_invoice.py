from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0081_added_timezone_to_country'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='synced_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Synced to MYOB at'),
        ),
    ]