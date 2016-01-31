from datetime import timedelta
from django.utils import timezone


def throttle(qs, throttle_config, param='first_message'):
    if throttle_config is None:
        return False

    # Return True if the next request would break any limit
    for count, seconds in throttle_config:
        f = {
            '%s__gte' % param: timezone.now() - timedelta(seconds=seconds)
        }
        if qs.filter(**f).count() + 1 > count:
            return (count, seconds)
    return False
