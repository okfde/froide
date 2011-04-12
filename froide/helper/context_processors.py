from django.conf import settings

def froide(request):
    return {"froide": settings.FROIDE_CONFIG}
