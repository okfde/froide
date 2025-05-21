"""
From: https://docs.djangoproject.com/en/1.11/topics/auth/passwords/#password-upgrading-without-requiring-a-login
"""

import hashlib

from django.contrib.auth.hashers import PBKDF2PasswordHasher


class PBKDF2WrappedSHA1PasswordHasher(PBKDF2PasswordHasher):
    algorithm = "pbkdf2_wrapped_sha1"

    def encode_sha1_hash(self, sha1_hash, salt, iterations=None):
        return super(PBKDF2WrappedSHA1PasswordHasher, self).encode(
            sha1_hash, salt, iterations
        )

    def encode(self, password, salt, iterations=None):
        _, _, sha1_hash = self.sha1_encode(password, salt).split("$", 2)
        return self.encode_sha1_hash(sha1_hash, salt, iterations)

    def sha1_encode(self, password, salt):
        # Taken from https://github.com/django/django/blob/5.0.14/django/contrib/auth/hashers.py#L666
        self._check_encode_args(password, salt)
        hash = hashlib.sha1((salt + password).encode()).hexdigest()
        return "%s$%s$%s" % (self.algorithm, salt, hash)
