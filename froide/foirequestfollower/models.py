import hmac

from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _, ungettext_lazy
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils.crypto import constant_time_compare

from froide.foirequest.models import FoiRequest
from froide.helper.email_sending import send_mail


class FoiRequestFollowerManager(models.Manager):
    def get_followable_requests(self, user):
        return FoiRequest.objects.exclude(
            user=user
        ).exclude(visibility=0)

    def follow(self, request, user, email=None, **kwargs):
        if user.is_authenticated:
            following = request.followed_by(user)
            if following:
                following.delete()
                return False
            FoiRequestFollower.objects.create(
                request=request, user=user, confirmed=True
            )
            return True
        else:
            following = request.followed_by(email)
            if following:
                return False
            try:
                following = FoiRequestFollower.objects.get(email=email)
                return None
            except FoiRequestFollower.DoesNotExist:
                following = FoiRequestFollower.objects.create(
                    request=request, email=email
                )
                following.send_follow_mail()
            return True

    def send_update(self, request, update_message, template=None):
        followers = FoiRequestFollower.objects.filter(
            request=request, confirmed=True
        )
        for follower in followers:
            FoiRequestFollower.send_update(
                {
                    request: {
                        'unfollow_link': follower.get_unfollow_link(),
                        'events': [update_message]
                    }
                },
                user=follower.user,
                email=follower.email,
                template=template
            )


class FoiRequestFollower(models.Model):
    request = models.ForeignKey(
        FoiRequest,
        on_delete=models.CASCADE,
        related_name='followers',
        verbose_name=_("Freedom of Information Request")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        verbose_name=_("User"), on_delete=models.CASCADE)
    email = models.CharField(max_length=255, blank=True)
    confirmed = models.BooleanField(default=False)
    timestamp = models.DateTimeField(_("Timestamp of Following"),
            auto_now_add=True)

    objects = FoiRequestFollowerManager()

    class Meta:
        get_latest_by = 'timestamp'
        ordering = ('timestamp',)
        verbose_name = _('Request Follower')
        verbose_name_plural = _('Request Followers')

    def __str__(self):
        return _("%(user)s follows %(request)s") % {
                "user": self.email or str(self.user),
                "request": self.request}

    def get_unfollow_link(self):
        return self.get_link(kind="unfollow")

    def get_follow_link(self):
        return self.get_link()

    def get_link(self, kind="follow"):
        return settings.SITE_URL + reverse(
            'foirequestfollower-confirm_%s' % kind,
            kwargs={
                'follow_id': self.id,
                'check': self.get_follow_secret()
            }
        )

    def get_follow_secret(self):
        to_sign = [self.email, str(self.request.id), str(self.id)]
        return hmac.new(
            settings.SECRET_KEY.encode('utf-8'),
            (".".join(to_sign)).encode('utf-8')
        ).hexdigest()

    def check_and_unfollow(self, check):
        secret = self.get_follow_secret()
        if constant_time_compare(check, secret):
            self.delete()
            return True
        return False

    def send_follow_mail(self):
        send_mail(
            _('Please confirm that you want to follow this request'),
            render_to_string("foirequestfollowers/confirm_follow.txt",
                {"request": self.request,
                "follow_link": self.get_follow_link(),
                "unfollow_link": self.get_unfollow_link(),
                "site_name": settings.SITE_NAME}),
            self.email,
            priority=True
        )

    @classmethod
    def send_update(cls, req_event_dict, user=None, email=None,
                    template=None):
        if user is None and email is None:
            return
        if template is None:
            template = 'foirequestfollower/update_follower.txt'

        count = len(req_event_dict)
        subject = ungettext_lazy(
            "Update on one followed request",
            "Update on %(count)s followed requests",
            count) % {
                'count': count
            }
        send_mail(
            subject,
            render_to_string(template,
                {
                    "req_event_dict": req_event_dict,
                    "count": count,
                    "user": user,
                    "site_name": settings.SITE_NAME
                }
            ),
            email or user.email,
            priority=False
        )
