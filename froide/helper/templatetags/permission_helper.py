from django import template

from ..auth import can_moderate_object

register = template.Library()


@register.filter
def has_perm(user, perm):
    return user.has_perm(perm)


@register.filter
def can_moderate(obj, request):
    return can_moderate_object(obj, request)
