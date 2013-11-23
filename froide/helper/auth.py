from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth import load_backend, login, get_user_model
from django.conf import settings


class EmailBackend(ModelBackend):
    def authenticate(self, username=None, password=None):
        try:
            validate_email(username)
        except ValidationError:
            return None
        user_model = get_user_model()
        try:
            user = user_model.objects.get(email=username)
            if user.check_password(password):
                return user
        except user_model.DoesNotExist:
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
