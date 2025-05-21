import logging
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Set

from django import forms
from django.conf import settings
from django.contrib.gis.geoip2 import GeoIP2
from django.core.cache import cache
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

import geoip2.database
import requests
from requests.exceptions import Timeout

from froide.helper.utils import get_client_ip

logger = logging.getLogger(__name__)


@dataclass
class Suspicion:
    message: str

    def __str__(self):
        return self.message


def suspicious_ip(request: HttpRequest) -> Optional[Suspicion]:
    ip = get_client_ip(request)
    if ip == "127.0.0.1":
        # Consider suspicious
        return Suspicion("localhost")

    target_countries = settings.FROIDE_CONFIG.get("target_countries", None)
    if target_countries:
        try:
            g = GeoIP2()
            info = g.country(ip)
            if info["country_code"] not in target_countries:
                return Suspicion("not target country")
        except Exception as e:
            logger.warning(e)

    try:
        if ip in get_tor_exit_ips():
            return Suspicion("tor exit node")
    except Exception as e:
        logger.error(e)

    if settings.FROIDE_CONFIG.get("suspicious_asn_provider_list"):
        asn_info = get_asn_info(ip)
        if asn_info is None:
            # No ASN info, consider suspicious
            return Suspicion("no ASN info")

        if suspicious_asn(asn_info.number):
            return Suspicion(
                "Bad ASN: {number} {organization}".format(**asdict(asn_info))
            )

    return None


@dataclass
class ASInfo:
    number: int
    organization: str


def get_asn_info(ip_address: str) -> Optional[ASInfo]:
    if not settings.GEOIP_PATH:
        return None
    asn_db_path = os.path.join(settings.GEOIP_PATH, "GeoLite2-ASN.mmdb")
    if not os.path.exists(asn_db_path):
        return None
    try:
        with geoip2.database.Reader(asn_db_path) as reader:
            result = reader.asn(ip_address)
    except geoip2.errors.AddressNotFoundError as e:
        logger.warning(e)
        return None
    return ASInfo(
        number=result.autonomous_system_number,
        organization=result.autonomous_system_organization,
    )


def suspicious_asn(asn: int) -> bool:
    try:
        return asn in get_suspicious_asns()
    except Exception as e:
        logger.warning(e)
        return False


ASN_LIST_TIMEOUT = 60 * 60 * 24


def get_suspicious_asns(refresh: bool = False) -> Set[int]:
    cache_key = "froide:suspicious_asns"
    result = cache.get(cache_key)
    if result and not refresh:
        return result

    asn_set = set()
    ASN_REGEX = re.compile(r"(?:^|[,;])(\d+)(?:$|[,;])", re.M)
    provider_list = settings.FROIDE_CONFIG.get("suspicious_asn_provider_list", [])
    for provider in provider_list:
        if provider.startswith("https://"):
            try:
                response = requests.get(provider, timeout=5)
            except Timeout:
                continue
            asn_set |= {int(x) for x in ASN_REGEX.findall(response.text)}
        else:
            asn_set |= {int(x) for x in provider.split(",") if x}
    cache.set(cache_key, asn_set, ASN_LIST_TIMEOUT)
    return asn_set


IP_RE = re.compile(r"ExitAddress (\S+)")
TOR_EXIT_IP_TIMEOUT = 60 * 15


def get_tor_exit_ips(refresh: bool = False) -> Set[str]:
    cache_key = "froide:tor_exit_ips"
    result = cache.get(cache_key)
    if result and not refresh:
        return result
    try:
        response = requests.get(
            "https://check.torproject.org/exit-addresses", timeout=5
        )
    except Timeout:
        return set()
    exit_ips = set(IP_RE.findall(response.text))
    cache.set(cache_key, exit_ips, TOR_EXIT_IP_TIMEOUT)
    return exit_ips


def too_many_actions(
    request: HttpRequest, action: str, threshold: int = 3, increment: bool = False
) -> bool:
    ip_address: str = get_client_ip(request)
    cache_key = "froide:limit_action:%s:%s" % (action, ip_address)
    count: int = cache.get(cache_key, 0)
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
    """
    Mixin that can triggers spam checking on forms
    """

    SPAM_PROTECTION = {}

    def __init__(self, *args, **kwargs) -> None:
        if not hasattr(self, "request"):
            self.request = kwargs.pop("request", None)
        kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        self.fields["phone"] = HoneypotField(
            required=False,
            label=_(
                "If you enter anything in this field " "your action will be blocked."
            ),
            widget=forms.TextInput(attrs={"required": True}),
        )
        if self._should_include_captcha():
            self.fields["test"] = forms.CharField(
                label=_("What is three plus four?"),
                widget=forms.TextInput(attrs={"class": "form-control"}),
                required=True,
                help_text=_(
                    "Please answer this question to give evidence you are human."
                ),
            )
        if self._should_include_timing():
            self.fields["time"] = forms.FloatField(
                initial=datetime.now(timezone.utc).timestamp(), widget=forms.HiddenInput
            )

    def _should_include_timing(self) -> bool:
        if not settings.FROIDE_CONFIG.get("spam_protection", True):
            return False
        return self.SPAM_PROTECTION.get("timing", False)

    def _should_skip_spam_check(self) -> bool:
        if not settings.FROIDE_CONFIG.get("spam_protection", True):
            return True
        return not self.request or self.request.user.is_authenticated

    def _should_include_captcha(self) -> bool:
        if self._should_skip_spam_check():
            return False
        if self.SPAM_PROTECTION.get("captcha") == "always":
            return True
        if self.SPAM_PROTECTION.get("captcha") == "ip" and self.request:
            return bool(suspicious_ip(self.request))
        if self._too_many_actions(increment=False):
            return True
        return False

    def clean_phone(self) -> str:
        """Check that nothing's been entered into the honeypot."""
        value = self.cleaned_data["phone"]
        if value:
            raise forms.ValidationError(self.fields["phone"].label)
        return value

    def clean_test(self) -> str:
        t = self.cleaned_data["test"]
        if t.lower().strip() not in ("7", str(_("seven"))):
            raise forms.ValidationError(_("Failed."))
        return t

    def clean_time(self) -> str:
        value = self.cleaned_data["time"]
        since = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) - datetime.fromtimestamp(value)
        if since < timedelta(seconds=5):
            raise forms.ValidationError(_("You filled this form out too quickly."))
        return value

    def _too_many_actions(self, increment=False) -> bool:
        if not self.request:
            return False
        action = self.SPAM_PROTECTION.get("action")
        if not action:
            return False
        return too_many_actions(
            self.request,
            action,
            threshold=self.SPAM_PROTECTION.get("action_limit", 3),
            increment=increment,
        )

    def clean(self) -> None:
        super().clean()
        if self._should_skip_spam_check():
            return
        too_many = self._too_many_actions(increment=True)
        should_block = self.SPAM_PROTECTION.get("action_block", False)
        if too_many and should_block and not self.cleaned_data.get("test"):
            raise forms.ValidationError(_("Too many actions."))
