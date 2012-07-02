from django.contrib.auth.backends import ModelBackend
from django.core.validators import email_re
from django.contrib.auth import models, load_backend, login
from django.conf import settings


class EmailBackend(ModelBackend):
    def authenticate(self, username=None, password=None):
        if email_re.search(username):
            try:
                user = models.User.objects.get(email=username)
                if user.check_password(password):
                    return user
            except models.User.DoesNotExist:
                return None
        return None


def login_user(request, user):
    if not hasattr(user, 'backend'):
        for backend in settings.AUTHENTICATION_BACKENDS:
            if user == load_backend(backend).get_user(user.pk):
                user.backend = backend
                break
    if hasattr(user, 'backend'):
        return login(request, user)
