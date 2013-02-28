from django.conf import settings
from django import template

register = template.Library()


def search_engine_query(query=None, domain=""):
    if query is None:
        return settings.FROIDE_CONFIG.get('search_engine_query', '') % {"query": "{{query}}", "domain": "{{domain}}"}
    else:
        return settings.FROIDE_CONFIG.get('search_engine_query', '') % {"query": query, "domain": domain}

register.simple_tag(search_engine_query)
