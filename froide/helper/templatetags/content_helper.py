from django import template
import calendar
import datetime
from django.utils.html import avoid_wrapping
from django.utils.timezone import is_aware, utc
from django.utils.formats import date_format
from django.utils.translation import ngettext_lazy, get_language

from ..content_urls import get_content_url

register = template.Library()


@register.simple_tag
def content_url(name):
    return get_content_url(name)


TIME_STRINGS = {
    'hour': ngettext_lazy('%d hour', '%d hours'),
    'minute': ngettext_lazy('%d minute', '%d minutes'),
    'second': ngettext_lazy('%d second', '%d seconds'),
}

TIME_VALUES = {
    'year': 60 * 60 * 24 * 365,
    # 'month': 60 * 60 * 24 * 30,
    # 'week': 60 * 60 * 24 * 7,
    'day': 60 * 60 * 24,
    'hour': 60 * 60,
    'minute': 60,
}


@register.filter
def relativetime(d):
    """
    Takes a datetime object and returns a relative time string

    If time < 60 minutes:
        - vor 43 Minuten
    If time < 24 hours:
        - vor 12 Stunden
    If time == current year:
        - 5. Feb.
    If time != current year:
        - 2. Februar 1988

    Adapted from:
    https://github.com/django/django/blob/8fa9a6d29efe2622872b4788190ea7c1bcb92019/django/utils/timesince.py
    (django/utils/timesince.py)

    Django date formats:
    https://docs.djangoproject.com/en/3.0/ref/templates/builtins/#date
    """

    def add_ago(time_str, lang_code):
        return f'vor {time_str}' if lang_code == 'de' else f'{time_str} ago'

    # Convert datetime.date to datetime.datetime for comparison.
    if not isinstance(d, datetime.datetime):
        d = datetime.datetime(d.year, d.month, d.day)

    now = datetime.datetime.now(utc if is_aware(d) else None)
    delta = now - d

    # Deal with leapyears by subtracing the number of leapdays
    leapdays = calendar.leapdays(d.year, now.year)
    if leapdays != 0:
        if calendar.isleap(d.year):
            leapdays -= 1
        elif calendar.isleap(now.year):
            leapdays += 1
    delta -= datetime.timedelta(leapdays)

    # ignore microseconds
    since = delta.days * 24 * 60 * 60 + delta.seconds
    if since <= 0:
        # d is in the future compared to now, stop processing.
        return avoid_wrapping(TIME_STRINGS['minute'] % 0)

    lang_code = get_language()
    result = ''

    if since <= TIME_VALUES['minute']:
        time_str = TIME_STRINGS['second'] % since
        result = add_ago(time_str, lang_code)
    elif since <= TIME_VALUES['hour']:
        minutes = since // TIME_VALUES['minute']
        time_str = TIME_STRINGS['minute'] % minutes
        result = add_ago(time_str, lang_code)
    elif since <= TIME_VALUES['day']:
        hours = since // TIME_VALUES['hour']
        time_str = TIME_STRINGS['hour'] % hours
        result = add_ago(time_str, lang_code)
    elif d.year == now.year:
        if lang_code == 'de':
            result = date_format(d, 'j. N')  # 18. Feb.
        else:
            result = date_format(d, 'M j.')  # Feb 18.
    else:
        if lang_code == 'de':
            result = date_format(d, 'j. N Y')  # 18. Feb. 2018
        else:
            result = date_format(d, 'M j. Y')  # Feb 18. 2018

    return avoid_wrapping(result)
