import os

from celery import Celery
from django.conf import settings  # noqa

from manage import set_env

set_env()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'r3sourcer.settings.prod')

app = Celery('r3sourcer')
app.config_from_object('r3sourcer.celeryconfig')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
