from django import template

from froide.helper.breadcrumbs import Breadcrumbs

register = template.Library()


@register.simple_tag(takes_context=True)
def get_breadcrumbs(context, view=None):
    return Breadcrumbs.from_view(view, context)
