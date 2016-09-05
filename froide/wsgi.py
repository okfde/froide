import os
import sys

# Calculate the path based on the location of the WSGI script.
apache_configuration = os.path.dirname(__file__)
project = os.path.dirname(apache_configuration)
workspace = os.path.join(project, '..')
sys.path.append(project)
sys.path.append(workspace)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'froide.settings')
os.environ.setdefault('DJANGO_CONFIGURATION', 'Production')

from django.conf import settings
from configurations.wsgi import get_wsgi_application

application = get_wsgi_application()

try:
    from whitenoise.django import DjangoWhiteNoise
    application = DjangoWhiteNoise(application)

    if settings.MEDIA_ROOT and settings.MEDIA_URL:
        application.add_files(settings.MEDIA_ROOT, prefix=settings.MEDIA_URL)
except ImportError:
    pass
