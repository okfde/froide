from django import template

from ..forms import CommentForm

register = template.Library()


@register.simple_tag(takes_context=True)
def get_froide_comment_form(context, object):
    request = context["request"]
    initial = {}
    if request.user.is_authenticated:
        initial["name"] = request.user.get_full_name()

    return CommentForm(object, initial=initial)
