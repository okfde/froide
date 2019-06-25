from django.utils import timezone

from froide.celery import app as celery_app

from .models import Upload


@celery_app.task(name='froide.upload.tasks.remove_expired_uploads')
def remove_expired_uploads():
    now = timezone.now()
    expired_uploads = Upload.objects.filter(expires__lt=now)
    for upload in expired_uploads:
        # Remove temporary file and delete object
        upload.delete()
