import os

from celery.task import task

from django.conf import settings
from django.utils import translation
from django.db import transaction
from django.core.files import File

from .models import FoiRequest, FoiAttachment
from .foi_mail import _process_mail, _fetch_mail
from .file_utils import convert_to_pdf


@task
def process_mail(mail):
    translation.activate(settings.LANGUAGE_CODE)

    def run(mail_string):
        try:
            _process_mail(mail_string)
        except Exception:
            transaction.rollback()
            raise
        else:
            transaction.commit()
            return None
    run = transaction.commit_manually(run)
    run(mail)


@task
def fetch_mail():
    for rfc_data in _fetch_mail():
        process_mail.delay(rfc_data)


@task
def detect_overdue():
    translation.activate(settings.LANGUAGE_CODE)
    for foirequest in FoiRequest.objects.get_to_be_overdue():
        foirequest.set_overdue()


@task
def detect_asleep():
    translation.activate(settings.LANGUAGE_CODE)
    for foirequest in FoiRequest.objects.get_to_be_asleep():
        foirequest.set_asleep()


@task
def classification_reminder():
    translation.activate(settings.LANGUAGE_CODE)
    for foirequest in FoiRequest.objects.get_unclassified():
        foirequest.send_classification_reminder()


@task
def count_same_foirequests(instance_id):
    translation.activate(settings.LANGUAGE_CODE)
    try:
        req = FoiRequest.objects.get(id=instance_id)
        count = FoiRequest.objects.filter(same_as=req).count()
        req.same_as_count = count
        req.save()
    except FoiRequest.DoesNotExist:
        pass


@task
def convert_attachment_task(instance_id):
    try:
        att = FoiAttachment.objects.get(pk=instance_id)
    except FoiAttachment.DoesNotExist:
        return
    return convert_attachment(att)


def convert_attachment(att):
    result_file = convert_to_pdf(
        att.file.path,
        binary_name=settings.FROIDE_CONFIG.get(
            'doc_conversion_binary'
        ),
        construct_call=settings.FROIDE_CONFIG.get(
            'doc_conversion_call_func'
        )
    )
    if result_file is None:
        return

    path, filename = os.path.split(result_file)
    new_file = File(file(result_file))

    if att.converted:
        new_att = att.converted
    else:
        if FoiAttachment.objects.filter(
                belongs_to=att.belongs_to,
                name=filename).exists():
            name, extension = filename.rsplit('.', 1)
            filename = '%s_converted.%s' % (name, extension)

        new_att = FoiAttachment(
            belongs_to=att.belongs_to,
            approved=False,
            filetype='application/pdf',
            is_converted=True
        )

    new_att.name = filename
    new_att.file = new_file
    new_att.size = new_file.size
    new_att.file.save(filename, new_file)
    new_att.save()
    att.converted = new_att
    att.save()
