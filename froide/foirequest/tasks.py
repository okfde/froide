from celery.task import task

from django.conf import settings
from django.utils import translation

from foirequest.models import FoiRequest
from foirequest.foi_mail import _process_mail, _fetch_mail

@task
def process_mail(mail_string):
    translation.activate(settings.LANGUAGE_CODE)
    return _process_mail(mail_string)

@task
def fetch_mail():
    for rfc_data in _fetch_mail():
        process_mail.delay(rfc_data)

@task
def detect_overdue():
    translation.activate(settings.LANGUAGE_CODE)
    for foirequest in FoiRequest.objects.get_overdue():
        foirequest.set_overdue()
