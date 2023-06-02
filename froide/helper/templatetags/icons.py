import functools

from django import template
from django.contrib.staticfiles import finders
from django.utils.html import mark_safe

register = template.Library()


@functools.lru_cache()
def _cached_render_svg(name):
    if not name.endswith(".svg"):
        return ""
    result = finders.find(name)
    if result is None:
        return ""
    with open(result, "r") as f:
        return f.read()


@register.simple_tag
def render_svg(name):
    return mark_safe(_cached_render_svg(name))
