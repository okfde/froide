from django.conf import settings

from .templatetags.block_helper import VAR_NAME, get_default_dict


def froide(request):
    return {"froide": settings.FROIDE_CONFIG}


def site_settings(request):
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_EMAIL": settings.SITE_EMAIL,
        "SITE_URL": settings.SITE_URL,
        "CURRENT_LANGUAGE_CODE": getattr(
            request, 'LANGUAGE_CODE', settings.LANGUAGE_CODE
        )
    }


def block_helper(request):
    return {VAR_NAME: get_default_dict()}
