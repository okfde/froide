import json
import os
import tempfile
from shutil import copyfile

from django.conf import settings

import factory
from factory.django import DjangoModelFactory

from froide.account.factories import UserFactory

from .models import Upload, states

TEST_PDF_URL = "test.pdf"
TEST_PDF_PATH = os.path.join(settings.MEDIA_ROOT, TEST_PDF_URL)
TEST_PDF_SIZE = os.path.getsize(TEST_PDF_PATH)


def generate_file_path():
    fd, path = tempfile.mkstemp(prefix="tus-upload-")
    os.close(fd)

    copyfile(TEST_PDF_PATH, path)

    print("generated path", path)
    return path


class UploadFactory(DjangoModelFactory):
    class Meta:
        model = Upload

    user = factory.LazyAttribute(lambda o: UserFactory())
    filename = TEST_PDF_URL
    temporary_file_path = generate_file_path()
    upload_length = TEST_PDF_SIZE
    upload_offset = TEST_PDF_SIZE
    state = states.RECEIVING
    upload_metadata = json.dumps(
        {
            "relativePath": "null",
            "name": TEST_PDF_URL,
            "type": "application/pdf",
            "filetype": "application/pdf",
            "filename": TEST_PDF_URL,
        }
    )
