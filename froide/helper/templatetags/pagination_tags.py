from django import template

register = template.Library()


@register.filter(name='listify')
def listify(value):
    return list(value)
