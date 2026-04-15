from django.conf import settings


def get_default_language():
    return settings.LANGUAGE_CODE


def get_language_choices():
    return settings.LANGUAGES
