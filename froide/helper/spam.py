import logging
import re
from datetime import timedelta, datetime

from django.core.cache import cache
from django import forms
from django.conf import settings
from django.contrib.gis.geoip2 import GeoIP2
from django.utils.translation import gettext_lazy as _

import requests

from froide.helper.utils import get_client_ip


logger = logging.getLogger(__name__)


def suspicious_ip(request):
    target_countries = settings.FROIDE_CONFIG.get('target_countries', None)
    if target_countries is None:
        return False
    try:
        g = GeoIP2()
        ip = get_client_ip(request)
        if ip == '127.0.0.1':
            # Consider suspicious
            return True
        info = g.country(ip)
        if info['country_code'] not in target_countries:
            return True
    except Exception as e:
        logger.warning(e)
    try:
        if ip in get_tor_exit_ips():
            return True
    except Exception as e:
        logger.error(e)
    return False


IP_RE = re.compile(r'ExitAddress (\S+)')
TOR_EXIT_IP_TIMEOUT = 60 * 15


def get_tor_exit_ips(refresh=False):
    cache_key = 'froide:tor_exit_ips'
    result = cache.get(cache_key)
    if result and not refresh:
        return result
    response = requests.get('https://check.torproject.org/exit-addresses')
    exit_ips = set(IP_RE.findall(response.text))
    cache.set(cache_key, exit_ips, TOR_EXIT_IP_TIMEOUT)
    return exit_ips


def too_many_actions(request, action, threshold=3, increment=False):
    ip_address = get_client_ip(request)
    cache_key = 'froide:limit_action:%s:%s' % (action, ip_address)
    count = cache.get(cache_key, 0)
    if increment:
        if count == 0:
            cache.set(cache_key, 1, timeout=60 * 60)
        else:
            try:
                cache.incr(cache_key)
            except ValueError:
                pass
    return count > threshold


class HoneypotField(forms.CharField):
    is_honeypot = True


class SpamProtectionMixin:
    '''
    Mixin that can triggers spam checking on forms
    '''
    SPAM_PROTECTION = {}

    def __init__(self, *args, **kwargs):
        if not hasattr(self, 'request'):
            self.request = kwargs.pop('request', None)
        kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['phone'] = HoneypotField(
            required=False,
            label=_('If you enter anything in this field '
                    'your action will be blocked.'),
            widget=forms.TextInput(
                attrs={'required': True}
            )
        )
        if self._should_include_captcha():
            self.fields['test'] = forms.CharField(
                label=_('What is three plus four?'),
                widget=forms.TextInput(
                    attrs={'class': 'form-control'}
                ),
                required=True,
                help_text=_('Please answer this question to give evidence you are human.'),
            )
        if self._should_include_timing():
            self.fields['time'] = forms.FloatField(
                initial=datetime.utcnow().timestamp(),
                widget=forms.HiddenInput
            )

    def _should_include_timing(self):
        if not settings.FROIDE_CONFIG.get('spam_protection', True):
            return False
        return self.SPAM_PROTECTION.get('timing', False)

    def _should_skip_spam_check(self):
        if not settings.FROIDE_CONFIG.get('spam_protection', True):
            return True
        return not self.request or self.request.user.is_authenticated

    def _should_include_captcha(self):
        if self._should_skip_spam_check():
            return False
        if self.SPAM_PROTECTION.get('captcha') == 'always':
            return True
        if self.SPAM_PROTECTION.get('captcha') == 'ip' and self.request:
            return suspicious_ip(self.request)
        if self._too_man_actions(increment=False):
            return True
        return False

    def clean_phone(self):
        """Check that nothing's been entered into the honeypot."""
        value = self.cleaned_data["phone"]
        if value:
            raise forms.ValidationError(self.fields["phone"].label)
        return value

    def clean_test(self):
        t = self.cleaned_data['test']
        if t.lower().strip() not in ('7', str(_('seven'))):
            raise forms.ValidationError(_('Failed.'))
        return t

    def clean_time(self):
        value = self.cleaned_data["time"]
        since = datetime.utcnow() - datetime.fromtimestamp(value)
        if since < timedelta(seconds=5):
            raise forms.ValidationError(
                _('You filled this form out too quickly.')
            )
        return value

    def _too_man_actions(self, increment=False):
        if not self.request:
            return False
        action = self.SPAM_PROTECTION.get('action')
        if not action:
            return False
        return too_many_actions(
            self.request, action,
            threshold=self.SPAM_PROTECTION.get('action_limit', 3),
            increment=increment
        )

    def clean(self):
        super().clean()
        if self._should_skip_spam_check():
            return
        too_many = self._too_man_actions(increment=True)
        should_block = self.SPAM_PROTECTION.get('action_block', False)
        if too_many and should_block and not self.cleaned_data.get('test'):
            raise forms.ValidationError(_('Too many actions.'))
