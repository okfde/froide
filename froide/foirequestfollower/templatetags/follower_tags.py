from django import template

from ..views import get_context

register = template.Library()


@register.inclusion_tag('foirequestfollower/_follow_form.html')
def follow_request_form(foirequest, request, follow_only=False, verbose=True):
    return get_context(foirequest, request, follow_only=follow_only,
                       verbose=verbose)
