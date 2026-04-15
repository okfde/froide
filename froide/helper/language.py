from django.conf import settings


def get_default_language():
    return settings.LANGUAGE_CODE


def get_language_choices():
    return settings.LANGUAGES


def get_user_language_choices():
    return getattr(settings, "USER_LANGUAGES", settings.LANGUAGES)
