import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "froide.settings")
os.environ.setdefault("DJANGO_CONFIGURATION", "Dev")

from configurations import importer  # noqa

importer.install(check_options=True)

from django.conf import settings  # noqa

from celery import Celery  # noqa

app = Celery("froide")
app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
