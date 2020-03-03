from datetime import timedelta

from django import template
from django.utils import timezone

register = template.Library()


@register.filter(name='deadline')
def deadline(date, num_days):
    if date is None:
        return
    days = timedelta(days=int(num_days))
    return date + days >= timezone.now().date()


@register.filter(name='no_future')
def no_future(date):
    if date is None:
        return
    return date <= timezone.now().date()
