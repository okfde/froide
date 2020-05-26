from django.conf import settings
from django.urls import path

from .export import EXPORT_MEDIA_PREFIX
from .views import ExportFileDetailView

MEDIA_PATH = settings.MEDIA_URL
# Split off domain and leading slash
if MEDIA_PATH.startswith('http'):
    MEDIA_PATH = MEDIA_PATH.split('/', 3)[-1]
else:
    MEDIA_PATH = MEDIA_PATH[1:]


urlpatterns = [
    path('%s%s/<uuid:token>.zip' % (
        MEDIA_PATH, EXPORT_MEDIA_PREFIX
    ), ExportFileDetailView.as_view(), name='account-download_export_token')
]
