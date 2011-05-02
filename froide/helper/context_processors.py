from django.conf import settings

def froide(request):
    return {"froide": settings.FROIDE_CONFIG}

def site_settings(request):
    return {"SITE_NAME": settings.SITE_NAME,
            "SITE_URL": settings.SITE_URL,
            "FROIDE_DRYRUN": settings.FROIDE_DRYRUN,
            "FROIDE_DRYRUN_DOMAIN": settings.FROIDE_DRYRUN_DOMAIN}
