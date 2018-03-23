import os

from django.conf import settings
from django.utils import translation
from django.utils.translation import ugettext_lazy as _
from django.db import transaction
from django.core.files import File

from froide.celery import app as celery_app
from froide.publicbody.models import PublicBody
from froide.helper.document import convert_to_pdf

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
def count_same_foirequests(instance_id):
    translation.activate(settings.LANGUAGE_CODE)
    try:
        count = FoiRequest.objects.filter(same_as_id=instance_id).count()
        FoiRequest.objects.filter(id=instance_id).update(same_as_count=count)
    except FoiRequest.DoesNotExist:
        pass


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

    result_filename = os.path.basename(result_file)
    result_name, result_ext = os.path.splitext(result_filename)

    if att.converted:
        new_att = att.converted
    else:
        name, ext = os.path.splitext(att.name)
        name = _('{name}_converted{ext}').format(name=name, ext=result_ext)

        new_att = FoiAttachment(
            name=name,
            belongs_to=att.belongs_to,
            approved=False,
            filetype='application/pdf',
            is_converted=True
        )

    with open(result_file, 'rb') as f:
        new_file = File(f)
        new_att.size = new_file.size
        new_att.file.save(new_att.name, new_file)
    new_att.save()
    att.converted = new_att
    att.save()
