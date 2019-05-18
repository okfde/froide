from django.conf.urls import url, include
from django.conf import settings
from django.utils.translation import pgettext_lazy as _

from ..views import (
    search, auth, shortlink, auth_message_attachment,
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
    url(_('url part', r'^make-request/'), include(make_request_urls)),
    # Translators: URL part
    url(_('url part', r'^requests/'), include(list_requests_urls)),
    # Translators: request URL
    url(_('url part', r'^request/'), include(request_urls)),
    # Translators: project URL
    url(_('url part', r'^project/'), include(project_urls)),

    # Translators: project URL
    url(_('url part', r'^account/'), include(account_urls)),

    # Translators: request URL
    url(_('url part', r'^search/'), search, name="foirequest-search"),
    # Translators: Short request URL
    url(_('url part', r"^r/(?P<obj_id>\d+)/?$"), shortlink,
        name="foirequest-shortlink"),
    # Translators: Short project URL
    url(_('url part', r"^p/(?P<obj_id>\d+)/?$"),
        project_shortlink, name="foirequest-project_shortlink"),
    # Translators: Short-request auth URL
    url(_('url part', r"^r/(?P<obj_id>\d+)/auth/(?P<code>[0-9a-f]+)/$"),
        auth, name="foirequest-auth"),
]

urlpatterns += [
    url(r'^%s%s/(?P<message_id>\d+)/(?P<attachment_name>.+)' % (
        settings.FOI_MEDIA_URL[1:], settings.FOI_MEDIA_PATH
    ), auth_message_attachment, name='foirequest-auth_message_attachment')
]
