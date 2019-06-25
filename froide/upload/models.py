import json
import os
import tempfile
import uuid

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.files import File

from django_fsm import FSMField, transition

from .utils import write_bytes_to_file


class states:
    INITIAL = 'initial'
    RECEIVING = 'receiving'
    SAVING = 'saving'
    DONE = 'done'


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
    guid = models.UUIDField(_('GUID'), default=uuid.uuid4, unique=True)

    state = FSMField(default=states.INITIAL)

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
            raise ValidationError(_('upload_offset should be >= 0.'))

    def write_data(self, upload_bytes, chunk_size):
        num_bytes_written = write_bytes_to_file(
            self.temporary_file_path,
            self.upload_offset,
            upload_bytes,
            makedirs=True
        )

        if num_bytes_written > 0:
            self.upload_offset += num_bytes_written
            self.save()

    @property
    def size(self):
        return self.upload_offset

    @property
    def content_type(self):
        return self.get_metadata().get('filetype')

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
            return TusFile(open(self.temporary_file_path, 'rb'))
        return None

    def generate_filename(self):
        return os.path.join('{}.bin'.format(uuid.uuid4()))

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self.filename:
            self.filename = self.generate_filename()
        return super().save(
            force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

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

    @transition(field=state, source=states.INITIAL, target=states.RECEIVING, conditions=[temporary_file_exists])
    def start_receiving(self):
        """
        State transition to indicate the first file chunk has been received successfully
        """
        # Trigger signal
        # signals.receiving.send(sender=self.__class__, instance=self)

    @transition(field=state, source=states.RECEIVING, target=states.SAVING, conditions=[is_complete])
    def start_saving(self):
        """
        State transition to indicate that the upload is complete, and that the temporary file will be transferred to
          its final destination.
        """
        # Trigger signal
        # signals.saving.send(sender=self.__class__, instance=self)

    @transition(field=state, source=states.SAVING, target=states.DONE)
    def finish(self):
        """
        State transition to indicate the upload is ready and the file is ready for access
        """
        # Trigger signal


class Upload(AbstractUpload):
    user = models.ForeignKey(
        get_user_model(), blank=True, null=True,
        on_delete=models.CASCADE
    )
