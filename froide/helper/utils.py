
def get_next(request):
    # This is not a view
    return request.GET.get("next", request.META.get("HTTP_REFERER", "/"))

