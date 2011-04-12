from django.conf import settings
from django import template

register = template.Library()

def search_engine_query(query=None, domain=""):
    if query is None:
        return settings.SEARCH_ENGINE_QUERY % {"query": "{{query}}", "domain": "{{domain}}"}
    else:
        return settings.SEARCH_ENGINE_QUERY % {"query": query, "domain": domain}

register.simple_tag(search_engine_query)
