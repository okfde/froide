import datetime
import importlib
import json
from typing import Dict, Optional, Union
from urllib.parse import parse_qs, urlsplit, urlunsplit

from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils.http import url_has_allowed_host_and_scheme, urlencode


def get_next(request: HttpRequest) -> str:
    # This is not a view
    return request.GET.get("next", request.META.get("HTTP_REFERER", "/"))


def render_code(
    code: int, request: HttpRequest, context: Optional[Dict[str, str]] = None
) -> HttpResponse:
    if context is None:
        context = {}
    return render(request, "%d.html" % code, context, status=code)


def render_400(request: HttpRequest) -> HttpResponse:
    return render_code(400, request)


def render_405(request: HttpRequest) -> HttpResponse:
    return render_code(405, request)


def render_403(
    request: HttpRequest, message: str = ""
) -> Union[HttpResponseRedirect, HttpResponse]:
    if not request.user.is_authenticated:
        return get_redirect(
            request, default="account-login", params={"next": request.get_full_path()}
        )
    return render_code(403, request, context={"message": message})


def get_client_ip(request: HttpRequest) -> str:
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[-1].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def get_redirect_url(
    request: HttpRequest,
    default: str = "/",
    next: None = None,
    allowed_hosts: None = None,
    params: Optional[Dict[str, str]] = None,
    keep_session: bool = False,
) -> str:
    if next is None:
        next = request.POST.get(
            "next", request.GET.get("next", request.session.get("next"))
        )
        if not keep_session and "next" in request.session:
            del request.session["next"]
    if next is None:
        keyword = request.GET.get("pk_keyword")
        if keyword and keyword.startswith("/"):
            next = keyword
    url_allowed = url_has_allowed_host_and_scheme(url=next, allowed_hosts=allowed_hosts)
    if not url_allowed:
        next = None
    if next is None and default is not None:
        if not default.startswith("/"):
            default = reverse(default)
        next = default
        url_allowed = url_has_allowed_host_and_scheme(
            url=next, allowed_hosts=allowed_hosts
        )
    if next is None or not url_allowed:
        next = request.META.get("HTTP_REFERER")
        url_allowed = url_has_allowed_host_and_scheme(
            url=next, allowed_hosts=allowed_hosts
        )
    if next is None or not url_allowed:
        next = "/"
    if params is not None:
        next = update_query_params(next, params)
    return next


def get_redirect(request: HttpRequest, **kwargs) -> HttpResponseRedirect:
    url = get_redirect_url(request, **kwargs)
    try:
        return redirect(url)
    except NoReverseMatch:
        return redirect("/")


def update_query_params(url: str, params: Dict[str, str]) -> str:
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
    return urlunsplit(
        (str(scheme), str(netloc), str(path), str(new_query_string), str(fragment))
    )


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj) -> Optional[str]:
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()


def to_json(obj) -> str:
    return json.dumps(obj, cls=DateTimeEncoder)


def is_ajax(request: HttpRequest) -> bool:
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def get_module_attr_from_dotted_path(path):
    module, attr = path.rsplit(".", 1)
    module = importlib.import_module(module)
    return getattr(module, attr)
