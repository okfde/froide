from __future__ import absolute_import

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'froide.settings')
os.environ.setdefault("DJANGO_CONFIGURATION", "Dev")

from configurations import importer  # noqa
importer.install(check_options=True)

from celery import Celery  # noqa
from django.conf import settings  # noqa


app = Celery('froide')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()
