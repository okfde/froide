from celery.task import task

from django.conf import settings
from django.utils import translation

from foirequest.foi_mail import _process_mail, _fetch_mail

@task
def process_mail(mail_string):
    translation.activate(settings.LANGUAGE_CODE)
    return _process_mail(mail_string)

@task
def fetch_mail():
    for rfc_data in _fetch_mail():
        process_mail.delay(rfc_data)
