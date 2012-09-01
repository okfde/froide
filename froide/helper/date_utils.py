# -*- coding: utf-8 -*-
from datetime import timedelta, datetime
import calendar

import pytz

from django.conf import settings

PYTZ_TIME_ZONE = pytz.timezone(settings.TIME_ZONE)


def calculate_month_range_de(date, months=1):
    """ Should calculate after German BGB Law § 188"""
    assert months < 12, "Can't calculate month_range > 12"
    tempdate = date + timedelta(days=(31 * months))
    m = tempdate.month
    y = tempdate.year
    d = tempdate.day
    last_day = calendar.monthrange(y, m)[1]
    if d > last_day:
        d = last_day
    due = datetime(y, m, d, 0, 0, 0)
    due = advance_after_holiday(due)
    due += timedelta(days=1)
    return PYTZ_TIME_ZONE.localize(due)


def calculate_workingday_range(date, days):
    one_day = timedelta(days=1)
    while days > 0:
        date += one_day
        if not is_holiday(date):
            days -= 1
    return date


def is_holiday(date):
    if settings.HOLIDAYS_WEEKENDS:
        if date.weekday() > 4:
            return True
    if (date.month, date.day) in settings.HOLIDAYS:
        return True
    if hasattr(settings, "HOLIDAYS_FOR_EASTER") and \
            settings.HOLIDAYS_FOR_EASTER:
        easter_sunday = calc_easter(date.year)
        easter_sunday = datetime(*easter_sunday)
        easter_holidays = [easter_sunday + timedelta(days=x) for x in settings.HOLIDAYS_FOR_EASTER]
        if date in easter_holidays:
            return True
    return False


def advance_after_holiday(date):
    one_day = timedelta(days=1)
    while is_holiday(date):
        date += one_day
    return date


# (c) Martin Diers, licensed under MIT
# taken from: http://code.activestate.com/recipes/576517-calculate-easter-western-given-a-year/
def calc_easter(year):
    "Returns Easter as a year, month, day tuple."
    a = year % 19
    b = year // 100
    c = year % 100
    d = (19 * a + b - b // 4 - ((b - (b + 8) // 25 + 1) // 3) + 15) % 30
    e = (32 + 2 * (b % 4) + 2 * (c // 4) - d - (c % 4)) % 7
    f = d + e - 7 * ((a + 11 * d + 22 * e) // 451) + 114
    month = f // 31
    day = f % 31 + 1
    return (year, month, day)

if __name__ == '__main__':
    print calculate_month_range_de(datetime(2011, 1, 31, 17, 16), 1)
