import os
import hashlib

from django.core.files.storage import FileSystemStorage


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
    return '%s_%d%s' % (path, num, ext)
