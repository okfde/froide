import hashlib
import os

from django.core.files.storage import FileSystemStorage
from django.db import models

from storages.backends.s3boto3 import S3Boto3Storage

from froide.helper.text_utils import slugify


def sha256(file):
    hash_sha256 = hashlib.sha256()
    file.seek(0)
    for chunk in iter(lambda: file.read(4096), b""):
        hash_sha256.update(chunk)
    file.seek(0)
    return hash_sha256.hexdigest()


class OverwriteStorage(FileSystemStorage):
    def get_available_name(self, name, max_length=None):
        # FIXME: max_length is ignored
        # If the filename already exists, remove it as if it was a true file system
        if self.exists(name):
            full_path = self.path(name)
            os.remove(full_path)
        return name


def delete_file_if_last_reference(
    instance: models.Model, field_name: str, delete_prefix: bool = False
):
    field_file = getattr(instance, field_name)
    more_references_exist = (
        instance.__class__.objects.filter(**{field_name: field_file})
        .exclude(pk=instance.pk)
        .exists()
    )
    if more_references_exist:
        return
    name = field_file.name
    field_file.delete(save=False)
    if delete_prefix:
        # Delete all files with that prefix (e.g. thumbnails)
        prefix_dir = os.path.dirname(name)
        prefix_name = os.path.basename(name)
        _dirs, dir_files = field_file.storage.listdir(prefix_dir)
        for dir_file in dir_files:
            if dir_file.startswith(prefix_name):
                field_file.storage.delete(os.path.join(prefix_dir, dir_file))


class MinioStorage(FileSystemStorage):
    """
    Minio S3 Storage

    This class will check if a file exists in the filesystem,
    if not it will try to fetch the file via S3.

    New files will always be stored on S3.
    """

    def _open(self, name, mode="rb"):
        "Read file from proper storage"
        if self.exists(name):
            return FileSystemStorage().open(name, mode)
        return S3Boto3Storage().open(name, mode)

    def _save(self, name, content):
        "Save files to S3 storage"
        return S3Boto3Storage().save(name, content)

    def delete(self, name):
        "Choose the proper file system for deletion"
        if self.exists(name):
            return FileSystemStorage().delete(name)
        return S3Boto3Storage().delete(name)

    def exists(self, name):
        "Check if file exists in the file system"
        if FileSystemStorage().exists(name):
            return FileSystemStorage().exists(name)
        return S3Boto3Storage().exists(name)

    def url(self, name):
        "Get URL for name"
        if self.exists(name):
            return FileSystemStorage().url(name)
        return S3Boto3Storage().url(name)

    def path(self, name):
        "Get path for name"
        if self.exists(name):
            return FileSystemStorage().path(name)
        return S3Boto3Storage().path(name)


class HashedFilenameStorage(FileSystemStorage):
    def get_hash_parts(self, content):
        hex_name = sha256(content)
        hex_name_02 = hex_name[:2]
        hex_name_24 = hex_name[2:4]
        hex_name_46 = hex_name[4:6]
        return [hex_name_02, hex_name_24, hex_name_46, hex_name]

    def _get_content_name(self, name, content):
        dir_name, file_name = os.path.split(name)
        # file_ext includes the dot.
        file_ext = os.path.splitext(file_name)[1].lower()
        parts = self.get_hash_parts(content)
        # Add extension to filename
        parts[-1] = parts[-1] + file_ext
        return os.path.join(dir_name, *parts)

    def get_available_name(self, name, max_length=None):
        """
        Doesn't matter, as hash filename identifies file uniquely
        """
        return name

    def _save(self, name, content):
        hashed_name = self._get_content_name(name=name, content=content)
        if self.exists(hashed_name):
            # if the file exists, just return the hashed name,
            # the file should be the same
            return hashed_name
        # if the file is new, DO call it
        return super(HashedFilenameStorage, self)._save(hashed_name, content)


def add_number_to_filename(filename, num):
    path, ext = os.path.splitext(filename)
    return "%s_%d%s" % (path, num, ext)


def make_filename(name: str) -> str:
    name = os.path.basename(name).rsplit(".", 1)
    return ".".join(slugify(n) for n in name)


def make_unique_filename(name, existing_names):
    slugified_name = make_filename(name)
    name = slugified_name
    index = 0
    while name in existing_names:
        index += 1
        name = add_number_to_filename(slugified_name, index)
    return name
