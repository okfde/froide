import json
import os
import tempfile
import uuid
from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import models
from django.urls import Resolver404, resolve
from django.utils.translation import gettext_lazy as _

from .utils import write_bytes_to_file


class UploadState(models.TextChoices):
    INITIAL = "initial"
    RECEIVING = "receiving"
    SAVING = "saving"
    DONE = "done"


class TusFile(File):
    """
    A TUS uploaded file, allow direct move
    """

    def temporary_file_path(self):
        """Return the full path of this file."""
        return self.file.name


class AbstractUpload(models.Model):
    """
    Abstract model for managing TUS uploads
    """

    guid = models.UUIDField(_("GUID"), default=uuid.uuid4, unique=True)

    state = models.CharField(
        choices=UploadState, max_length=50, default=UploadState.INITIAL
    )

    upload_offset = models.BigIntegerField(default=0)
    upload_length = models.BigIntegerField(default=-1)

    upload_metadata = models.TextField(blank=True)

    filename = models.CharField(max_length=255, blank=True)

    temporary_file_path = models.CharField(max_length=4096, null=True)

    expires = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def get_metadata(self):
        return json.loads(self.upload_metadata)

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        if self.upload_offset < 0:
            raise ValidationError(_("upload_offset should be >= 0."))

    def write_data(self, upload_bytes, chunk_size):
        num_bytes_written = write_bytes_to_file(
            self.temporary_file_path, self.upload_offset, upload_bytes, makedirs=True
        )

        if num_bytes_written > 0:
            self.upload_offset += num_bytes_written
            self.save()

    @property
    def size(self):
        return self.upload_offset

    @property
    def content_type(self):
        return self.get_metadata().get("filetype")

    @property
    def name(self):
        return self.filename

    def delete(self, *args, **kwargs):
        if self.temporary_file_exists():
            os.remove(self.temporary_file_path)
        super().delete(*args, **kwargs)

    def get_file(self):
        if not self.is_complete():
            return None
        if self.temporary_file_exists():
            return TusFile(open(self.temporary_file_path, "rb"))
        return None

    def generate_filename(self):
        return os.path.join("{}.bin".format(uuid.uuid4()))

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if not self.filename:
            self.filename = self.generate_filename()
        return super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

    def is_complete(self):
        return self.upload_offset == self.upload_length

    def temporary_file_exists(self):
        return self.temporary_file_path and os.path.isfile(self.temporary_file_path)

    def get_or_create_temporary_file(self):
        if not self.temporary_file_path:
            fd, path = tempfile.mkstemp(prefix="tus-upload-")
            os.close(fd)
            self.temporary_file_path = path
            self.save()
        assert os.path.isfile(self.temporary_file_path)
        return self.temporary_file_path

    def start_receiving(self):
        """
        State transition to indicate the first file chunk has been received successfully
        """
        if self.state != UploadState.INITIAL:
            raise ValidationError(
                _("Cannot start receiving, upload is not in initial state.")
            )
        if not self.temporary_file_exists():
            raise ValidationError(
                _("Cannot start receiving, temporary file does not exist.")
            )
        self.state = UploadState.RECEIVING
        self.save(update_fields=["state"])

    def ensure_saving(self):
        if self.state == UploadState.RECEIVING:
            self.start_saving()

    def start_saving(self):
        """
        State transition to indicate that the upload is complete, and that the temporary file will be transferred to
          its final destination.
        """
        if self.state != UploadState.RECEIVING:
            raise ValidationError(
                _("Cannot start saving, upload is not in receiving state.")
            )
        if not self.is_complete():
            raise ValidationError(_("Cannot start saving, upload is not complete."))
        self.state = UploadState.SAVING
        self.save(update_fields=["state"])

    def finish(self):
        """
        State transition to indicate the upload is ready and the file is ready for access
        """
        if self.state != UploadState.SAVING:
            raise ValidationError(_("Cannot finish, upload is not in saving state."))
        self.state = UploadState.DONE
        self.save(update_fields=["state"])


class UploadManager(models.Manager):
    def get_by_url(self, upload_url, user=None, token=None):
        parsed_upload_url = urlparse(upload_url)
        upload_path = parsed_upload_url.path
        try:
            match = resolve(upload_path)
        except Resolver404:
            return None
        guid = match.kwargs.get("guid")
        if guid is None:
            return None
        try:
            return Upload.objects.get(user=user, token=token, guid=guid)
        except Upload.DoesNotExist:
            return None


class Upload(AbstractUpload):
    user = models.ForeignKey(
        get_user_model(), blank=True, null=True, on_delete=models.CASCADE
    )
    token = models.UUIDField(null=True, blank=True)

    objects = UploadManager()
