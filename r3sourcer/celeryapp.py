import os

from celery import Celery
from django.conf import settings  # noqa


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'r3sourcer.settings')

app = Celery('r3sourcer')
app.config_from_object('r3sourcer.celeryconfig')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
