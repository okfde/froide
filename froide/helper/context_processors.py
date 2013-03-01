from django.conf import settings


def froide(request):
    return {"froide": settings.FROIDE_CONFIG}


def site_settings(request):
    return {"SITE_NAME": settings.SITE_NAME,
            "SITE_EMAIL": settings.SITE_EMAIL,
            "SITE_URL": settings.SITE_URL,
            "LANGUAGE_CODE": settings.LANGUAGE_CODE}
