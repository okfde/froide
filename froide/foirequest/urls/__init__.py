from django.urls import path, re_path, include
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
    path(pgettext_lazy('url part', 'make-request/'), include(make_request_urls)),
    # Translators: URL part
    path(pgettext_lazy('url part', 'requests/'), include(list_requests_urls)),
    # Translators: request URL
    path(pgettext_lazy('url part', 'request/'), include(request_urls)),
    # Translators: project URL
    path(pgettext_lazy('url part', 'project/'), include(project_urls)),

    # Translators: project URL
    path(pgettext_lazy('url part', 'account/'), include(account_urls)),

    # Translators: request URL
    path(pgettext_lazy('url part', 'search/'), search, name="foirequest-search"),
    # Translators: Short request URL
    # Translators: Short project URL
    re_path(pgettext_lazy('url part', r"^p/(?P<obj_id>\d+)/?$"),
        project_shortlink, name="foirequest-project_shortlink"),
    # Translators: Short-request auth URL
    re_path(pgettext_lazy('url part', r"^r/(?P<obj_id>\d+)/auth/(?P<code>[0-9a-f]+)/$"),
        auth, name="foirequest-auth"),
    re_path(pgettext_lazy('url part', r"^r/(?P<obj_id>\d+)(?P<url_path>[\w/\-/]+)$"), shortlink,
        name="foirequest-shortlink_url"),
    re_path(pgettext_lazy('url part', r"^r/(?P<obj_id>\d+)"), shortlink,
        name="foirequest-shortlink"),
]

MEDIA_PATH = settings.MEDIA_URL
# Split off domain and leading slash
if MEDIA_PATH.startswith('http'):
    MEDIA_PATH = MEDIA_PATH.split('/', 3)[-1]
else:
    MEDIA_PATH = MEDIA_PATH[1:]


urlpatterns += [
    path('%s%s/<int:message_id>/<str:attachment_name>' % (
        MEDIA_PATH, settings.FOI_MEDIA_PATH
    ), AttachmentFileDetailView.as_view(), name='foirequest-auth_message_attachment')
]
