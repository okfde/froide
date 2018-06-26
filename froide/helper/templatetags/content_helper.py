from django import template

from ..content_urls import get_content_url

register = template.Library()


@register.simple_tag
def content_url(name):
    return get_content_url(name)
