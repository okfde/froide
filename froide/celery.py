from __future__ import absolute_import

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'froide.settings')
os.environ.setdefault("DJANGO_CONFIGURATION", "Dev")

from configurations import importer
importer.install(check_options=True)

from celery import Celery
from django.conf import settings


app = Celery('froide')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(settings.INSTALLED_APPS, related_name='tasks')
