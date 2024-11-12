import logging
import os
from datetime import timedelta
from functools import partial

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import mail_managers
from django.db import transaction
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _

from celery.exceptions import SoftTimeLimitExceeded

from froide.celery import app as celery_app
from froide.publicbody.models import PublicBody
from froide.upload.models import Upload

from .foi_mail import _fetch_mail, _process_mail, get_foi_mail_client
from .models import FoiAttachment, FoiProject, FoiRequest
from .notifications import batch_update_requester, send_classification_reminder

logger = logging.getLogger(__name__)


@celery_app.task(name="froide.foirequest.tasks.process_mail", acks_late=True)
def process_mail(*args, **kwargs):
    translation.activate(settings.LANGUAGE_CODE)

    with transaction.atomic():
        _process_mail(*args, **kwargs)


@celery_app.task(name="froide.foirequest.tasks.fetch_mail", expires=60)
def fetch_mail():
    for mail_uid, rfc_data in _fetch_mail():
        process_mail.delay(rfc_data, mail_uid=mail_uid)


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
def batch_update_requester_task():
    return batch_update_requester()


@celery_app.task
def classification_reminder():
    translation.activate(settings.LANGUAGE_CODE)
    for foirequest in FoiRequest.objects.get_unclassified():
        send_classification_reminder(foirequest)


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

    kwargs.update(
        {
            "project": project,
            "publicbody": pb,
            "subject": project.title,
            "user": project.user,
            "body": project.description,
            "public": project.public,
            "reference": project.reference,
            "tags": [t.name for t in project.tags.all()],
            "project_order": sequence,
        }
    )
    service = CreateRequestFromProjectService(kwargs)
    foirequest = service.execute()

    if project.request_count == project.foirequest_set.all().count():
        project.status = FoiProject.STATUS_READY
        project.save()

    return foirequest.pk


@celery_app.task
def create_project_messages(foirequest_ids, user_id, **form_data):
    for req_id in foirequest_ids:
        create_project_message.delay(req_id, user_id, **form_data)


@celery_app.task
def create_project_message(foirequest_id, user_id, **form_data):
    from django.contrib.auth import get_user_model

    from froide.foirequest.forms.message import SendMessageForm

    User = get_user_model()

    try:
        foirequest = FoiRequest.objects.get(id=foirequest_id)
    except FoiRequest.DoesNotExist:
        # request does not exist anymore?
        return
    assert foirequest.project

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    # Send to public body's default email
    form_data["to"] = foirequest.public_body.email
    form = SendMessageForm(foirequest=foirequest, data=form_data)
    if form.is_valid():
        form.save(user=user, bulk=True)


@celery_app.task
def set_project_request_status_bulk(foirequest_ids, user_id, **form_data):
    for req_id in foirequest_ids:
        set_project_request_status.delay(req_id, user_id, **form_data)


@celery_app.task
def set_project_request_status(foirequest_id, user_id, **form_data):
    from django.contrib.auth import get_user_model

    from froide.foirequest.forms.request import FoiRequestStatusForm

    User = get_user_model()

    try:
        foirequest = FoiRequest.objects.get(id=foirequest_id)
    except FoiRequest.DoesNotExist:
        # request does not exist anymore?
        return
    assert foirequest.project

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    # Set foirequest status via form
    form = FoiRequestStatusForm(foirequest=foirequest, data=form_data)
    if form.is_valid():
        form.save(user=user)


@celery_app.task(name="froide.foirequest.tasks.convert_attachment_task", time_limit=60)
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
        name = _("{name}_ocr{ext}").format(name=name, ext=".pdf")

        ocred_att = FoiAttachment.objects.create(
            name=name,
            belongs_to=att.belongs_to,
            approved=False,
            filetype="application/pdf",
            is_converted=True,
            can_approve=att.can_approve,
        )

    att.converted = ocred_att
    att.can_approve = False
    att.approved = False
    att.save()

    transaction.on_commit(
        partial(
            ocr_pdf_task.delay,
            att.pk,
            ocred_att.pk,
        )
    )


def convert_attachment(att):
    from filingcabinet.pdf_utils import convert_to_pdf

    output_bytes = convert_to_pdf(
        att.file.path,
        binary_name=settings.FROIDE_CONFIG.get("doc_conversion_binary"),
        construct_call=settings.FROIDE_CONFIG.get("doc_conversion_call_func"),
    )
    if output_bytes is None:
        return

    if att.converted:
        new_att = att.converted
    else:
        name, ext = os.path.splitext(att.name)
        name = _("{name}_converted{ext}").format(name=name, ext=".pdf")

        new_att = FoiAttachment(
            name=name,
            belongs_to=att.belongs_to,
            approved=False,
            filetype="application/pdf",
            is_converted=True,
            can_approve=att.can_approve,
        )

    new_file = ContentFile(output_bytes)
    new_att.size = new_file.size
    new_att.file.save(new_att.name, new_file)
    new_att.save()
    att.converted = new_att
    att.can_approve = False
    att.approved = False
    att.save()


@celery_app.task(
    name="froide.foirequest.tasks.convert_images_to_pdf_task",
    time_limit=60 * 5,
    soft_time_limit=60 * 4,
)
def convert_images_to_pdf_task(att_ids, target_id, instructions, can_approve=True):
    from filingcabinet.pdf_utils import convert_images_to_ocred_pdf

    att_qs = FoiAttachment.objects.filter(id__in=att_ids)
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
        att_qs.update(can_approve=can_approve)
        target.delete()
        return

    new_file = ContentFile(pdf_bytes)
    target.size = new_file.size
    target.file.save(target.name, new_file)
    target.save()


@celery_app.task(
    name="froide.foirequest.tasks.ocr_pdf_task",
    time_limit=60 * 5,
    soft_time_limit=60 * 4,
)
def ocr_pdf_task(att_id, target_id, can_approve=True):
    from filingcabinet.pdf_utils import run_ocr

    try:
        attachment = FoiAttachment.objects.get(pk=att_id)
    except FoiAttachment.DoesNotExist:
        return
    try:
        target = FoiAttachment.objects.get(pk=target_id)
    except FoiAttachment.DoesNotExist:
        return

    try:
        pdf_bytes = run_ocr(
            attachment.file.path,
            language=settings.TESSERACT_LANGUAGE
            if settings.TESSERACT_LANGUAGE
            else settings.LANGUAGE_CODE,
            timeout=180,
        )
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


@celery_app.task(
    name="froide.foirequest.tasks.redact_attachment_task",
    time_limit=60 * 6,
    soft_time_limit=60 * 5,
)
def redact_attachment_task(att_id, target_id, instructions):
    from filingcabinet.pdf_utils import run_ocr

    from froide.helper.redaction import redact_file

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

    logger.info("Trying redaction of %s", attachment.id)

    try:
        pdf_bytes = redact_file(attachment.file, instructions)
    except Exception:
        logger.error("PDF redaction error", exc_info=True)
        pdf_bytes = None

    if pdf_bytes is None:
        logger.info("Redaction failed %s", attachment.id)
        # Redaction has failed, remove empty attachment
        if attachment.redacted:
            attachment.redacted = None
        if attachment.is_redacted:
            attachment.approved = True
            attachment.can_approve = True
        attachment.pending = False
        attachment.save()

        if not target.file:
            target.delete()
        return

    logger.info("Redaction successful %s", attachment.id)
    pdf_file = ContentFile(pdf_bytes)
    target.size = pdf_file.size
    target.file.save(target.name, pdf_file, save=False)

    logger.info("Trying OCR %s", target.id)

    try:
        pdf_bytes = run_ocr(
            target.file.path,
            language=settings.TESSERACT_LANGUAGE
            if settings.TESSERACT_LANGUAGE
            else settings.LANGUAGE_CODE,
            timeout=60 * 4,
        )
    except SoftTimeLimitExceeded:
        pdf_bytes = None

    if pdf_bytes is not None:
        logger.info("OCR successful %s", target.id)
        pdf_file = ContentFile(pdf_bytes)
        target.size = pdf_file.size
        target.file.save(target.name, pdf_file, save=False)
    else:
        logger.info("OCR failed %s", target.id)

    target.can_approve = True
    target.pending = False
    target.approve_and_save()
    FoiAttachment.attachment_approved.send(sender=target, user=None, redacted=True)


@celery_app.task(name="froide.foirequest.tasks.move_upload_to_attachment")
def move_upload_to_attachment(att_id, upload_id):
    try:
        att = FoiAttachment.objects.get(pk=att_id)
    except FoiAttachment.DoesNotExist:
        return

    try:
        upload = Upload.objects.get(pk=upload_id)
    except FoiAttachment.DoesNotExist:
        return

    file = upload.get_file()
    if file:
        att.pending = False
        att.file.save(att.name, file, save=True)
    upload.finish()
    upload.delete()

    if att.can_convert_to_pdf():
        convert_attachment_task.delay(att.id)


@celery_app.task(
    name="froide.foirequest.tasks.unpack_zipfile_attachment_task", time_limit=360
)
def unpack_zipfile_attachment_task(instance_id):
    from .utils import unpack_zipfile_attachment

    try:
        att = FoiAttachment.objects.get(pk=instance_id)
    except FoiAttachment.DoesNotExist:
        return

    unpack_zipfile_attachment(att)


@celery_app.task(name="froide.foirequest.tasks.remove_old_drafts", time_limit=10)
def remove_old_drafts():
    from .models import FoiMessage

    FoiMessage.objects.filter(
        is_draft=True, last_modified_at__lt=timezone.now() - timedelta(days=30)
    ).delete()


@celery_app.task(
    name="froide.foirequest.tasks.warn_on_unprocessed_mail", time_limit=120
)
def warn_on_unprocessed_mail():
    with get_foi_mail_client() as client:
        status, count = client.select("Inbox")
        typ, [msg_ids] = client.search(None, "FLAGGED")
        if len(msg_ids) > 0:
            mail_managers(
                _("Unprocessed FOI Mail: {count}").format(count=len(msg_ids)),
                _("There are unprocessed FOI Mails, inform system administrators!"),
            )
