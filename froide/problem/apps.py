from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ProblemConfig(AppConfig):
    name = 'froide.problem'
    verbose_name = _('Problems')
