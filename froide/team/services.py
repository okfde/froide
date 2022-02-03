import hashlib
import hmac

from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.crypto import constant_time_compare
from django.utils.translation import gettext_lazy as _

from froide.helper.email_sending import send_mail

from .models import Team


def can_use_team(user):
    if not user.is_authenticated:
        return False
    in_team = Team.objects.get_for_user(user).exists()
    return in_team or user.has_perm("team.can_use_teams")


class TeamService(object):
    def __init__(self, member):
        self.member = member

    def generate_invite_secret(self):
        to_sign = [str(self.member.pk), str(self.member.email)]
        return hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            (".".join(to_sign)).encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

    def check_invite_secret(self, secret):
        return constant_time_compare(secret, self.generate_invite_secret())

    def send_team_invite(self, invited_by):
        secret = self.generate_invite_secret()
        url_kwargs = {
            "pk": self.member.pk,
            "secret": secret,
        }
        url = "%s%s" % (
            settings.SITE_URL,
            reverse("team-join", kwargs=url_kwargs),
        )
        message = render_to_string(
            "team/emails/team_invite.txt",
            {
                "url": url,
                "name": invited_by.get_full_name(),
                "site_name": settings.SITE_NAME,
                "site_url": settings.SITE_URL,
            },
        )
        # Translators: Mail subject
        send_mail(
            str(_("Team invite from %(name)s") % {"name": invited_by.get_full_name()}),
            message,
            self.member.email,
            priority=True,
        )
