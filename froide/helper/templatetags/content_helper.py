import calendar
import datetime

from django import template
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.html import avoid_wrapping
from django.utils.http import urlencode
from django.utils.translation import gettext as _
from django.utils.translation import ngettext_lazy, pgettext

from ..content_urls import get_content_url

register = template.Library()


@register.simple_tag
def content_url(name):
    return get_content_url(name)


TIME_STRINGS = {
    "hour": ngettext_lazy("%d hour", "%d hours"),
    "minute": ngettext_lazy("%d minute", "%d minutes"),
    "second": ngettext_lazy("%d second", "%d seconds"),
}

TIME_VALUES = {
    "year": 60 * 60 * 24 * 365,
    # 'month': 60 * 60 * 24 * 30,
    # 'week': 60 * 60 * 24 * 7,
    "day": 60 * 60 * 24,
    "hour": 60 * 60,
    "minute": 60,
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

    d = timezone.localtime(d)
    # Convert datetime.date to datetime.datetime for comparison.
    if not isinstance(d, datetime.datetime):
        d = datetime.datetime(d.year, d.month, d.day)

    now = timezone.now()
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
        return avoid_wrapping(TIME_STRINGS["minute"] % 0)

    result = ""
    if since <= TIME_VALUES["day"]:
        if since <= TIME_VALUES["minute"]:
            time_str = TIME_STRINGS["second"] % since
        elif since <= TIME_VALUES["hour"]:
            minutes = since // TIME_VALUES["minute"]
            time_str = TIME_STRINGS["minute"] % minutes
        else:
            hours = since // TIME_VALUES["hour"]
            time_str = TIME_STRINGS["hour"] % hours
        result = _("{time_str} ago").format(time_str=time_str)
    elif d.year == now.year:
        result = _("on {date}").format(
            date=date_format(d, pgettext("date format without year", "M j."))
        )
    else:
        result = _("on {date}").format(date=date_format(d, "SHORT_DATE_FORMAT"))
    return avoid_wrapping(result)


@register.filter
def make_login_redirect_url(url):
    return reverse(settings.LOGIN_URL) + "?" + urlencode({"next": url})


@register.filter
def fontawesome_filetype_icon(attachment):
    if attachment.is_pdf:
        return "fa-file-pdf-o"
    elif attachment.is_word:
        return "fa-file-word-o"
    elif attachment.is_image:
        return "fa-file-image-o"
    elif attachment.is_excel:
        return "fa-file-excel-o"
    elif attachment.is_text:
        return "fa-file-text-o"
    elif attachment.is_archive:
        return "fa-file-archive-o"
    elif attachment.is_powerpoint:
        return "fa-file-powerpoint-o"

    return "fa-file-o"
