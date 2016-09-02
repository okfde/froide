from datetime import timedelta

from django.utils import timezone
from django.core.mail import mail_managers
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from froide.helper.date_utils import format_seconds


def throttle(qs, throttle_config, date_param='first_message'):
    if throttle_config is None:
        return False

    # Return True if the next request would break any limit
    for count, seconds in throttle_config:
        f = {
            '%s__gte' % date_param: timezone.now() - timedelta(seconds=seconds)
        }
        if qs.filter(**f).count() + 1 > count:
            return (count, seconds)
    return False


def check_throttle(user, klass):
    if user.is_authenticated and not user.trusted():
        throttle_settings = settings.FROIDE_CONFIG.get('request_throttle', None)
        qs, date_param = klass.objects.get_throttle_filter(user)
        throttle_kind = throttle(qs, throttle_settings, date_param=date_param)
        if throttle_kind:
            mail_managers(_('User exceeded request limit'), user.pk)
            return _('You exceeded your request limit of {count} requests in {time}.'
                    ).format(count=throttle_kind[0],
                             time=format_seconds(throttle_kind[1])
            )
