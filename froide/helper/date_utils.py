import pytz
from datetime import timedelta

from django.conf import settings

PYTZ_TIME_ZONE = pytz.timezone(settings.TIME_ZONE)

def convert_to_local(date, offset_in_seconds=None):
    if offset_in_seconds is not None:
        date = date + timedelta(seconds=offset_in_seconds)
    date = pytz.utc.localize(date)
    return date.astimezone(PYTZ_TIME_ZONE)

