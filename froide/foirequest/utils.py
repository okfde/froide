from datetime import timedelta
import unicodedata
import warnings

from django.utils import timezone
from django.core.mail import mail_managers
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from django.utils import six
from django.utils.encoding import force_text
from django.utils.six.moves.urllib.parse import urlparse

from froide.helper.date_utils import format_seconds


def throttle(qs, throttle_config, date_param='first_message'):
    if throttle_config is None:
        return False

    # Return True if the next request would break any limit
    for count, seconds in throttle_config:
        f = {
            '%s__gte' % date_param: timezone.now() - timedelta(seconds=seconds)
        }
        if qs.filter(**f).count() + 1 > count:
            return (count, seconds)
    return False


def check_throttle(user, klass):
    if user.is_authenticated and not user.trusted():
        throttle_settings = settings.FROIDE_CONFIG.get('request_throttle', None)
        qs, date_param = klass.objects.get_throttle_filter(user)
        throttle_kind = throttle(qs, throttle_settings, date_param=date_param)
        if throttle_kind:
            mail_managers(_('User exceeded request limit'), user.pk)
            return _('You exceeded your request limit of {count} requests in {time}.'
                    ).format(count=throttle_kind[0],
                             time=format_seconds(throttle_kind[1])
            )

# Forward port from master
# https://github.com/django/django/blob/master/django/utils/http.py


def is_safe_url(url, host=None, allowed_hosts=None, require_https=False):
    """
    Return ``True`` if the url is a safe redirection (i.e. it doesn't point to
    a different host and uses a safe scheme).
    Always returns ``False`` on an empty url.
    If ``require_https`` is ``True``, only 'https' will be considered a valid
    scheme, as opposed to 'http' and 'https' with the default, ``False``.
    """
    if url is not None:
        url = url.strip()
    if not url:
        return False
    if six.PY2:
        try:
            url = force_text(url)
        except UnicodeDecodeError:
            return False
    if allowed_hosts is None:
        allowed_hosts = set()
    if host:
        warnings.warn(
            "The host argument is deprecated, use allowed_hosts instead.",
            stacklevel=2,
        )
        # Avoid mutating the passed in allowed_hosts.
        allowed_hosts = allowed_hosts | {host}
    # Chrome treats \ completely as / in paths but it could be part of some
    # basic auth credentials so we need to check both URLs.
    return (_is_safe_url(url, allowed_hosts, require_https=require_https) and
            _is_safe_url(url.replace('\\', '/'), allowed_hosts, require_https=require_https))


def _is_safe_url(url, allowed_hosts, require_https=False):
    # Chrome considers any URL with more than two slashes to be absolute, but
    # urlparse is not so flexible. Treat any url with three slashes as unsafe.
    if url.startswith('///'):
        return False
    url_info = urlparse(url)
    # Forbid URLs like http:///example.com - with a scheme, but without a hostname.
    # In that URL, example.com is not the hostname but, a path component. However,
    # Chrome will still consider example.com to be the hostname, so we must not
    # allow this syntax.
    if not url_info.netloc and url_info.scheme:
        return False
    # Forbid URLs that start with control characters. Some browsers (like
    # Chrome) ignore quite a few control characters at the start of a
    # URL and might consider the URL as scheme relative.
    if unicodedata.category(url[0])[0] == 'C':
        return False
    scheme = url_info.scheme
    # Consider URLs without a scheme (e.g. //example.com/p) to be http.
    if not url_info.scheme and url_info.netloc:
        scheme = 'http'
    valid_schemes = ['https'] if require_https else ['http', 'https']
    return ((not url_info.netloc or url_info.netloc in allowed_hosts) and
            (not scheme or scheme in valid_schemes))
