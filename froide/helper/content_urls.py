from typing import Union

from django.conf import settings
from django.utils.safestring import SafeString

CONTENT_URLS = settings.FROIDE_CONFIG.get("content_urls", {})


def get_content_url(name: Union[SafeString, str]) -> str:
    return CONTENT_URLS.get(name, "/")
