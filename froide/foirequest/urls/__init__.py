from django.conf.urls import url, include
from django.conf import settings
from django.utils.translation import pgettext

from ..views import (
    search, auth, shortlink, auth_message_attachment,
    project_shortlink
)

from . import (
    make_request_urls,
    list_requests_urls,
    request_urls,
    project_urls
)


urlpatterns = [
    # Translators: request URL
    url(r'^%s/' % pgettext('url part', 'make-request'), include(make_request_urls)),
    # Translators: URL part
    url(r'^%s/' % pgettext('url part', 'requests'), include(list_requests_urls)),
    # Translators: request URL
    url(r'^%s/' % pgettext('url part', 'request'), include(request_urls)),
    # Translators: project URL
    url(r'^%s/' % pgettext('url part', 'project'), include(project_urls)),


    # Translators: request URL
    url(r'^%s/' % pgettext('url part', 'search'), search, name="foirequest-search"),
    # Translators: Short request URL
    url(r"^%s/(?P<obj_id>\d+)/?$" % pgettext('url part', 'r'), shortlink, name="foirequest-shortlink"),
    # Translators: Short project URL
    url(r"^%s/(?P<obj_id>\d+)/?$" % pgettext('url part', 'p'), project_shortlink, name="foirequest-project_shortlink"),
    # Translators: Short-request auth URL
    url(r"^%s/(?P<obj_id>\d+)/auth/(?P<code>[0-9a-f]+)/$" % pgettext('url part', 'r'), auth, name="foirequest-auth"),
]

urlpatterns += [
    url(r'^%s%s/(?P<message_id>\d+)/(?P<attachment_name>.+)' % (
        settings.FOI_MEDIA_URL[1:], settings.FOI_MEDIA_PATH
    ), auth_message_attachment, name='foirequest-auth_message_attachment')
]
