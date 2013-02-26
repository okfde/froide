from django.shortcuts import render


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
