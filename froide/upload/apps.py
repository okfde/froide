from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class UploadConfig(AppConfig):
    name = 'froide.upload'
    verbose_name = _('Upload')
