import os
import logging

from django.conf import settings
from django.utils import translation
from django.utils.translation import ugettext_lazy as _
from django.db import transaction
from django.core.files.base import ContentFile

from celery.exceptions import SoftTimeLimitExceeded

from froide.celery import app as celery_app
from froide.publicbody.models import PublicBody
from froide.helper.document import convert_to_pdf, convert_images_to_ocred_pdf
from froide.document.pdf_utils import PDFProcessor
from froide.helper.redaction import redact_file

from .models import FoiRequest, FoiMessage, FoiAttachment, FoiProject
from .foi_mail import _process_mail, _fetch_mail


@celery_app.task(name='froide.foirequest.tasks.process_mail',
                 acks_late=True, time_limit=60)
def process_mail(*args, **kwargs):
    translation.activate(settings.LANGUAGE_CODE)

    with transaction.atomic():
        _process_mail(*args, **kwargs)


@celery_app.task(name='froide.foirequest.tasks.fetch_mail', expires=60)
def fetch_mail():
    for rfc_data in _fetch_mail():
        process_mail.delay(rfc_data)


@celery_app.task
def detect_overdue():
    translation.activate(settings.LANGUAGE_CODE)
    for foirequest in FoiRequest.objects.get_to_be_overdue():
        foirequest.set_overdue()


@celery_app.task
def detect_asleep():
    translation.activate(settings.LANGUAGE_CODE)
    for foirequest in FoiRequest.objects.get_to_be_asleep():
        foirequest.set_asleep()


@celery_app.task
def classification_reminder():
    translation.activate(settings.LANGUAGE_CODE)
    for foirequest in FoiRequest.objects.get_unclassified():
        foirequest.send_classification_reminder()


@celery_app.task
def check_delivery_status(message_id, count=None, extended=False):
    try:
        message = FoiMessage.objects.get(id=message_id)
    except FoiMessage.DoesNotExist:
        return
    message.check_delivery_status(count=count, extended=extended)


@celery_app.task
def create_project_requests(project_id, publicbody_ids, **kwargs):
    for seq, pb_id in enumerate(publicbody_ids):
        create_project_request.delay(project_id, pb_id, sequence=seq, **kwargs)


@celery_app.task
def create_project_request(project_id, publicbody_id, sequence=0, **kwargs):
    from .services import CreateRequestFromProjectService

    try:
        project = FoiProject.objects.get(id=project_id)
    except FoiProject.DoesNotExist:
        # project does not exist anymore?
        return

    try:
        pb = PublicBody.objects.get(id=publicbody_id)
    except PublicBody.DoesNotExist:
        # pb was deleted?
        return

    kwargs.update({
        'project': project,
        'publicbody': pb,

        'subject': project.title,
        'user': project.user,
        'body': project.description,
        'public': project.public,
        'reference': project.reference,
        'tags': [t.name for t in project.tags.all()],

        'project_order': sequence
    })
    service = CreateRequestFromProjectService(kwargs)
    foirequest = service.execute()

    if project.request_count == project.foirequest_set.all().count():
        project.status = FoiProject.STATUS_READY
        project.save()

    return foirequest.pk


@celery_app.task(name='froide.foirequest.tasks.convert_attachment_task',
                 time_limit=60)
def convert_attachment_task(instance_id):
    try:
        att = FoiAttachment.objects.get(pk=instance_id)
    except FoiAttachment.DoesNotExist:
        return
    if att.can_convert_to_pdf():
        return convert_attachment(att)


def ocr_pdf_attachment(att):
    if att.converted:
        ocred_att = att.converted
    else:
        name, ext = os.path.splitext(att.name)
        name = _('{name}_ocr{ext}').format(name=name, ext='.pdf')

        ocred_att = FoiAttachment.objects.create(
            name=name,
            belongs_to=att.belongs_to,
            approved=False,
            filetype='application/pdf',
            is_converted=True,
            can_approve=att.can_approve,
        )

    att.converted = ocred_att
    att.can_approve = False
    att.approved = False
    att.save()

    ocr_pdf_task.delay(
        att.pk, ocred_att.pk,
    )


def convert_attachment(att):
    output_bytes = convert_to_pdf(
        att.file.path,
        binary_name=settings.FROIDE_CONFIG.get(
            'doc_conversion_binary'
        ),
        construct_call=settings.FROIDE_CONFIG.get(
            'doc_conversion_call_func'
        )
    )
    if output_bytes is None:
        return

    if att.converted:
        new_att = att.converted
    else:
        name, ext = os.path.splitext(att.name)
        name = _('{name}_converted{ext}').format(name=name, ext='.pdf')

        new_att = FoiAttachment(
            name=name,
            belongs_to=att.belongs_to,
            approved=False,
            filetype='application/pdf',
            is_converted=True,
            can_approve=att.can_approve
        )

    new_file = ContentFile(output_bytes)
    new_att.size = new_file.size
    new_att.file.save(new_att.name, new_file)
    new_att.save()
    att.converted = new_att
    att.can_approve = False
    att.approved = False
    att.save()


@celery_app.task(name='froide.foirequest.tasks.convert_images_to_pdf_task',
                 time_limit=60 * 5, soft_time_limit=60 * 4)
def convert_images_to_pdf_task(att_ids, target_id, instructions, can_approve=True):
    att_qs = FoiAttachment.objects.filter(
        id__in=att_ids
    )
    att_map = {a.id: a for a in att_qs}
    atts = [att_map[a_id] for a_id in att_ids]
    try:
        target = FoiAttachment.objects.get(id=target_id)
    except FoiAttachment.DoesNotExist:
        return

    paths = [a.file.path for a in atts]
    try:
        pdf_bytes = convert_images_to_ocred_pdf(paths, instructions=instructions)
    except SoftTimeLimitExceeded:
        pdf_bytes = None

    if pdf_bytes is None:
        att_qs.update(
            can_approve=can_approve
        )
        target.delete()
        return

    new_file = ContentFile(pdf_bytes)
    target.size = new_file.size
    target.file.save(target.name, new_file)
    target.save()


@celery_app.task(name='froide.foirequest.tasks.ocr_pdf_task',
                 time_limit=60 * 5, soft_time_limit=60 * 4)
def ocr_pdf_task(att_id, target_id, can_approve=True):
    try:
        attachment = FoiAttachment.objects.get(pk=att_id)
    except FoiAttachment.DoesNotExist:
        return
    try:
        target = FoiAttachment.objects.get(pk=target_id)
    except FoiAttachment.DoesNotExist:
        return

    processor = PDFProcessor(
        attachment.file.path, language=settings.LANGUAGE_CODE
    )
    try:
        pdf_bytes = processor.run_ocr(timeout=180)
    except SoftTimeLimitExceeded:
        pdf_bytes = None

    if pdf_bytes is None:
        attachment.can_approve = can_approve
        attachment.save()
        target.delete()
        return

    new_file = ContentFile(pdf_bytes)
    target.size = new_file.size
    target.file.save(target.name, new_file)
    target.save()


@celery_app.task(name='froide.foirequest.tasks.redact_attachment_task',
                 time_limit=60 * 6, soft_time_limit=60 * 5)
def redact_attachment_task(att_id, target_id, instructions):
    try:
        attachment = FoiAttachment.objects.get(pk=att_id)
    except FoiAttachment.DoesNotExist:
        return

    if att_id != target_id:
        try:
            target = FoiAttachment.objects.get(pk=target_id)
        except FoiAttachment.DoesNotExist:
            return
    else:
        target = attachment

    logging.info('Trying redaction of %s with instructions %s',
                 attachment.id, instructions
    )

    try:
        pdf_bytes = redact_file(attachment.file, instructions)
    except Exception:
        logging.error("PDF redaction error", exc_info=True)
        pdf_bytes = None

    if pdf_bytes is None:
        logging.info('Redaction failed %s', attachment.id)
        # Redaction has failed, remove empty attachment
        if attachment.redacted:
            attachment.redacted = None
        if attachment.is_redacted:
            attachment.approved = True
            attachment.can_approve = True
        attachment.save()

        if not target.file:
            target.delete()
        return

    logging.info('Redaction successful %s', attachment.id)
    pdf_file = ContentFile(pdf_bytes)
    target.size = pdf_file.size
    target.file.save(target.name, pdf_file, save=False)

    logging.info('Trying OCR %s', target.id)
    processor = PDFProcessor(
        target.file.path, language=settings.LANGUAGE_CODE
    )
    try:
        pdf_bytes = processor.run_ocr(timeout=60 * 4)
    except SoftTimeLimitExceeded:
        pdf_bytes = None

    if pdf_bytes is not None:
        logging.info('OCR successful %s', target.id)
        pdf_file = ContentFile(pdf_bytes)
        target.size = pdf_file.size
        target.file.save(target.name, pdf_file, save=False)
    else:
        logging.info('OCR failed %s', target.id)

    target.can_approve = True
    target.approve_and_save()
