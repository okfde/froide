import base64
import io
import zlib
from typing import Protocol, Tuple

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _

from cryptography.fernet import Fernet
from slugify import slugify

MimeAttachment = Tuple[str, bytes, str]


class ProofAttachment(Protocol):
    def get_mime_attachment(self) -> MimeAttachment:
        ...


class TemporaryProof:
    def __init__(self, name: str, file: io.BytesIO):
        self.name = name
        self.file_bytes = file.read()

    def get_mime_attachment(self):
        filename = "{}.jpg".format(slugify(self.name))
        return (filename, self.file_bytes, Proof.mimetype)


class Proof(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=True)

    timestamp = models.DateTimeField(default=timezone.now, editable=False)

    file = models.FileField(upload_to="proofs/")
    # key is 32 Bytes long, 44 ASCII chars in base64
    key = models.CharField(max_length=44)

    mimetype = "image/jpeg"

    def __str__(self):
        return _("{name} (uploaded {timestamp})").format(
            name=self.name, timestamp=date_format(self.timestamp, "SHORT_DATE_FORMAT")
        )

    def save_with_file(self, file):
        # Key is given as Base64 encoded Bytes
        self.key = Fernet.generate_key().decode("ascii")
        fernet = Fernet(self.key)
        filename = "{}_{}.enc.gz".format(self.timestamp.isoformat(), self.user_id)

        self.file.save(
            filename, ContentFile(zlib.compress(fernet.encrypt(file.read())))
        )

    def get_file_bytes(self):
        fernet = Fernet(self.key)
        try:
            return fernet.decrypt(zlib.decompress(self.file.read()))
        except Exception:
            return b""

    def get_image_data_url(self):
        return "data:{};base64,{}".format(
            self.mimetype, base64.b64encode(self.get_file_bytes()).decode("utf-8")
        )

    def get_mime_attachment(self):
        filename = "{}.jpg".format(slugify(self.name))
        return (filename, self.get_file_bytes(), self.mimetype)

    def delete(self):
        self.file.delete(save=False)
        super().delete()
