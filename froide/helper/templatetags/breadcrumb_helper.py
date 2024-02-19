from django import template
from django.urls import NoReverseMatch, reverse

register = template.Library()


def normalize_breadcrumb(breadcrumb):
    if type(breadcrumb) == tuple:
        if type(breadcrumb[1]) == str:
            try:
                breadcrumb = (breadcrumb[0], reverse(breadcrumb[1]))
            except NoReverseMatch:
                pass

        return breadcrumb
    else:
        return (breadcrumb, None)


@register.simple_tag(takes_context=True)
def get_breadcrumbs(context, view=None):
    if hasattr(view, "get_breadcrumbs") and callable(view.get_breadcrumbs):
        view.get_breadcrumbs(context)

    if hasattr(view, "breadcrumbs"):
        return map(normalize_breadcrumb, view.breadcrumbs)


@register.filter
def has_link(value):
    return type(value) == tuple and len(value) == 2
