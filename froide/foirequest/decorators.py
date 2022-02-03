from functools import wraps

from django.shortcuts import get_object_or_404

from froide.helper.utils import render_403

from .auth import (
    can_moderate_foirequest,
    can_moderate_pii_foirequest,
    can_write_foirequest,
)
from .models import FoiRequest


def allow_foirequest_if_any(*checks):
    if not checks:
        raise ValueError("Checks must not be empty")

    def decorator(func):
        @wraps(func)
        def inner(request, slug, *args, **kwargs):
            foirequest = get_object_or_404(FoiRequest, slug=slug)
            for check in checks:
                if check(foirequest, request):
                    return func(request, foirequest, *args, **kwargs)
            return render_403(request)

        return inner

    return decorator


allow_write_foirequest = allow_foirequest_if_any(can_write_foirequest)
allow_moderate_foirequest = allow_foirequest_if_any(can_moderate_foirequest)
allow_write_or_moderate_foirequest = allow_foirequest_if_any(
    can_write_foirequest, can_moderate_foirequest
)
allow_write_or_moderate_pii_foirequest = allow_foirequest_if_any(
    can_write_foirequest, can_moderate_pii_foirequest
)
