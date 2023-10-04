from django import template

register = template.Library()


@register.filter
def is_tuple(value):
    return type(value) == tuple
