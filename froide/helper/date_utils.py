from datetime import timedelta, datetime
import calendar

from django.conf import settings
from django.utils import timezone
from django.utils.timesince import timeuntil

MONTHS_IN_YEAR = 12


def format_seconds(seconds):
    now = timezone.now()
    future = now + timedelta(seconds=seconds)
    return timeuntil(future, now)


def calculate_month_range_de(date, months=1):
    """ Should calculate after German BGB Law § 130 and § 188"""

    current_tz = timezone.get_current_timezone()

    # make sure we are in our timezone
    if not isinstance(date, datetime):
        date = datetime(date.year, date.month, date.day, 23, 59, 59)
        date = current_tz.localize(date, is_dst=None)

    date = current_tz.normalize(date.astimezone(current_tz))

    tempdate = date
    if date.hour >= 22:  # After 22h next working day is receival
        tempdate = date + timedelta(days=1)
    # Receival only on working days
    tempdate = advance_after_holiday(tempdate)
    # § 187 (1) BGB Fristbeginn
    tempdate += timedelta(days=1)
    # § 188 BGB (2) Fristende
    # endigt im Falle des § 187 Abs. 1 mit dem Ablauf desjenigen Tages
    # der letzten Woche oder des letzten Monats, welcher durch seine
    # Benennung oder seine Zahl dem Tage entspricht, in den das Ereignis
    # oder der Zeitpunkt fällt,
    m = tempdate.month + (months % MONTHS_IN_YEAR)
    y = tempdate.year + (months // MONTHS_IN_YEAR) + ((m - 1) // MONTHS_IN_YEAR)
    m = m % MONTHS_IN_YEAR
    if m == 0:
        m = 12
    d = tempdate.day
    # § 188 BGB (3) Fristende
    last_day = calendar.monthrange(y, m)[1]
    if d > last_day:
        d = last_day
    due = datetime(y, m, d, 0, 0, 0)
    # Move Fristende to after holiday.
    due = advance_after_holiday(due)
    # Return first day after Fristende
    due += timedelta(days=1)
    return current_tz.localize(due)


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
        easter_holidays = [
            (easter_sunday + timedelta(days=x)).date()
            for x in settings.HOLIDAYS_FOR_EASTER
        ]
        if date.date() in easter_holidays:
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
    print(calculate_month_range_de(datetime(2011, 1, 31, 17, 16), 1))
