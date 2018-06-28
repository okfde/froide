try:
    from urllib.parse import parse_qs, urlsplit, urlunsplit
except ImportError:
    from urlparse import parse_qs, urlsplit, urlunsplit

from django.shortcuts import render, redirect
from django.urls import reverse, NoReverseMatch
from django.utils.http import is_safe_url, urlencode


def get_next(request):
    # This is not a view
    return request.GET.get("next", request.META.get("HTTP_REFERER", "/"))


def render_code(code, request, context={}):
    return render(request, "%d.html" % code, context,
            status=code)


def render_400(request):
    return render_code(400, request)


def render_405(request):
    return render_code(405, request)


def render_403(request, message=''):
    return render_code(403, request,
            context={"message": message})


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[-1].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_redirect_url(request, default='/', next=None, allowed_hosts=None,
                     params=None):
    if next is None:
        next = request.POST.get('next',
            request.GET.get('next', request.session.get('next')))
        if 'next' in request.session:
            del request.session['next']
    if next is None:
        keyword = request.GET.get('pk_keyword')
        if keyword and keyword.startswith('/'):
            next = keyword
    if not is_safe_url(url=next, allowed_hosts=allowed_hosts):
        next = None
    if next is None and default is not None:
        if not default.startswith('/'):
            default = reverse(default)
        next = default
    if next is None or not is_safe_url(url=next, allowed_hosts=allowed_hosts):
        next = request.META.get('HTTP_REFERER')
    if next is None or not is_safe_url(url=next, allowed_hosts=allowed_hosts):
        next = '/'
    if params is not None:
        next = update_query_params(next, params)
    return next


def get_redirect(request, **kwargs):
    url = get_redirect_url(request, **kwargs)
    try:
        return redirect(url)
    except NoReverseMatch:
        return redirect('/')


def update_query_params(url, params):
    """
    Given a URL, update the query parameters and return the
    modified URL.

    >>> update_query_params('http://example.com?foo=bar&biz=baz', {'foo': 'stuff'})
    'http://example.com?foo=stuff&biz=baz'

    """
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    query_params = parse_qs(query_string)
    query_params.update(params)
    new_query_string = urlencode(query_params, doseq=True)
    return urlunsplit((str(scheme), str(netloc), str(path),
                       str(new_query_string), str(fragment)))
