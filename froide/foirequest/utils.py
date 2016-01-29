from datetime import timedelta
from django.utils import timezone


def throttle(qs, throttle_config, param='first_message'):
    if throttle_config is None:
        return False

    count, days = throttle_config

    kwargs = {
        '%s__gte' % param: timezone.now() - timedelta(days=days)
    }
    # Return True if the next request would break the limit
    return qs.filter(**kwargs).count() + 1 > count
