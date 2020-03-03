from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class LetterConfig(AppConfig):
    name = 'froide.letter'
    verbose_name = _('Letter')
