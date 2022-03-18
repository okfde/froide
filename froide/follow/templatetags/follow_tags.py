from django import template
from django.template.loader import render_to_string

from ..models import follow_registry
from ..utils import get_context

register = template.Library()


@register.inclusion_tag("follow/show_follow.html", takes_context=True)
def show_follow(context, slug, content_object):
    request = context["request"]
    configuration = follow_registry.get_by_slug(slug)
    return get_context(request, content_object, configuration)


@register.simple_tag(takes_context=True)
def follow_form(context, slug, content_object, follow_only=False, verbose=True):
    request = context["request"]
    configuration = follow_registry.get_by_slug(slug)
    context = get_context(
        request, content_object, configuration, follow_only=follow_only, verbose=verbose
    )
    return render_to_string("follow/_follow_form.html", context, request)
