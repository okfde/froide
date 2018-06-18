from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.http import is_safe_url


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


def get_redirect_url(request, default='/', next=None):
    if next is None:
        next = request.POST.get('next',
            request.GET.get('next', request.session.get('next')))
        if 'next' in request.session:
            del request.session['next']
    if next is None:
        keyword = request.GET.get('pk_keyword')
        if keyword.startswith('/'):
            next = keyword
    if not is_safe_url(url=next, host=request.get_host()):
        next = None
    if next is None and default is not None:
        if not default.startswith('/'):
            default = reverse(default)
        next = default
    if next is None or not is_safe_url(url=next, host=request.get_host()):
        next = request.META.get('HTTP_REFERER')
    if next is None or not is_safe_url(url=next, host=request.get_host()):
        next = '/'
    return next


def get_redirect(request, **kwargs):
    url = get_redirect_url(request, **kwargs)
    return redirect(url)
