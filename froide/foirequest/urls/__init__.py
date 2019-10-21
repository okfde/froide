from django.conf.urls import url, include
from django.conf import settings
from django.utils.translation import pgettext_lazy

from ..views import (
    search, auth, shortlink, AttachmentFileDetailView,
    project_shortlink
)

from . import (
    make_request_urls,
    list_requests_urls,
    request_urls,
    project_urls,
    account_urls
)


urlpatterns = [
    # Translators: request URL
    url(pgettext_lazy('url part', r'^make-request/'), include(make_request_urls)),
    # Translators: URL part
    url(pgettext_lazy('url part', r'^requests/'), include(list_requests_urls)),
    # Translators: request URL
    url(pgettext_lazy('url part', r'^request/'), include(request_urls)),
    # Translators: project URL
    url(pgettext_lazy('url part', r'^project/'), include(project_urls)),

    # Translators: project URL
    url(pgettext_lazy('url part', r'^account/'), include(account_urls)),

    # Translators: request URL
    url(pgettext_lazy('url part', r'^search/'), search, name="foirequest-search"),
    # Translators: Short request URL
    url(pgettext_lazy('url part', r"^r/(?P<obj_id>\d+)/(?P<url_part>[\w/\-]*)$"), shortlink,
        name="foirequest-shortlink"),
    # Translators: Short project URL
    url(pgettext_lazy('url part', r"^p/(?P<obj_id>\d+)/?$"),
        project_shortlink, name="foirequest-project_shortlink"),
    # Translators: Short-request auth URL
    url(pgettext_lazy('url part', r"^r/(?P<obj_id>\d+)/auth/(?P<code>[0-9a-f]+)/$"),
        auth, name="foirequest-auth"),
]

MEDIA_PATH = settings.MEDIA_URL
# Split off domain and leading slash
if MEDIA_PATH.startswith('http'):
    MEDIA_PATH = MEDIA_PATH.split('/', 3)[-1]
else:
    MEDIA_PATH = MEDIA_PATH[1:]


urlpatterns += [
    url(r'^%s%s/(?P<message_id>\d+)/(?P<attachment_name>.+)' % (
        MEDIA_PATH, settings.FOI_MEDIA_PATH
    ), AttachmentFileDetailView.as_view(), name='foirequest-auth_message_attachment')
]
