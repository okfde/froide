import os
import sys

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils._os import safe_join
from django.utils.importlib import import_module
from django.template.loaders.app_directories import Loader

fs_encoding = sys.getfilesystemencoding() or sys.getdefaultencoding()

theme_template_dir = None

if getattr(settings, 'FROIDE_THEME', None) is not None:
    app = settings.FROIDE_THEME
    try:
        mod = import_module(app)
    except ImportError, e:
        raise ImproperlyConfigured('ImportError %s: %s' % (app, e.args[0]))
    theme_template_dir = os.path.join(
            os.path.dirname(mod.__file__), 'templates')
    if os.path.isdir(theme_template_dir):
        theme_template_dir = theme_template_dir.decode(fs_encoding)
    else:
        theme_template_dir = None


class ThemeLoader(Loader):
    is_usable = theme_template_dir is not None

    def get_template_sources(self, template_name, template_dirs=None):
        """
        Returns the absolute paths to "template_name", when appended to
        the FROIDE_THEME app.
        """
        if not template_dirs:
            template_dirs = [theme_template_dir]
        for template_dir in template_dirs:
            try:
                yield safe_join(template_dir, template_name)
            except UnicodeDecodeError:
                # The template dir name was a bytestring that wasn't valid UTF-8.
                raise
            except ValueError:
                # The joined path was located outside of template_dir.
                pass

_loader = ThemeLoader()  # noqa
