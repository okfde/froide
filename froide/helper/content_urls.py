from django.conf import settings

CONTENT_URLS = settings.FROIDE_CONFIG.get('content_urls', {})


def get_content_url(name):
    return CONTENT_URLS.get(name, '/')
