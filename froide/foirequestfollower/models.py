import hmac

from django.db import models
from django.contrib.postgres.fields import JSONField
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.dispatch import Signal

from froide.foirequest.models import FoiRequest
from froide.helper.email_sending import mail_registry

REFERENCE_PREFIX = 'follow-'

User = get_user_model()


follow_request_email = mail_registry.register(
    'foirequestfollower/emails/confirm_follow',
    ('action_url', 'foirequest', 'user')
)

update_follower_email = mail_registry.register(
    'foirequestfollower/emails/update_follower',
    ('count', 'user', 'update_list')
)

batch_update_follower_email = mail_registry.register(
    'foirequestfollower/emails/batch_update_follower',
    ('count', 'user', 'update_list')
)


class FoiRequestFollowerManager(models.Manager):
    def get_followable_requests(self, user):
        return FoiRequest.objects.exclude(
            user=user
        ).exclude(visibility=0)

    def request_followed_by(self, foirequest, user=None, email=None):
        if email is not None:
            return FoiRequestFollower.objects.filter(
                request=foirequest,
                email=email,
                confirmed=True
            ).exists()
        else:
            return FoiRequestFollower.objects.filter(
                request=foirequest,
                user=user
            ).exists()

    def follow(self, foirequest, user, email=None, **extra_data):
        if user.is_authenticated:
            return self.user_follow(foirequest, user, extra_data)
        else:
            return self.email_follow(foirequest, email, extra_data)

    def user_follow(self, foirequest, user, extra_data):
        try:
            follower = FoiRequestFollower.objects.get(
                request=foirequest,
                user=user
            )
            FoiRequestFollower.unfollowing.send(sender=follower)
            follower.delete()
            return False
        except FoiRequestFollower.DoesNotExist:
            pass
        follower = FoiRequestFollower.objects.create(
            request=foirequest, user=user, confirmed=True,
            context=extra_data or None
        )
        FoiRequestFollower.followed.send(sender=follower)
        return True

    def get_user_for_email(self, email):
        try:
            return User.objects.get(
                is_active=True, email=email
            )
        except User.DoesNotExist:
            return None

    def email_follow(self, foirequest, email, extra_data):
        try:
            # Confirmed email follow
            follower = FoiRequestFollower.objects.get(
                request=foirequest,
                email=email,
            )
        except FoiRequestFollower.DoesNotExist:
            follower = None

        user = self.get_user_for_email(email)

        if follower is None:
            follower = FoiRequestFollower.objects.create(
                request=foirequest, email=email,
                context=extra_data or None
            )
        follower.send_confirm_follow_mail(extra_data, user=user)
        return True

    def send_update(self, user_or_email, update_list, batch=False):
        if not user_or_email:
            return
        user, email = None, None
        if isinstance(user_or_email, str):
            email = user_or_email
        else:
            user = user_or_email

        count = len(update_list)
        context = {
            'user': user,
            'email': email,
            'count': count,
            'update_list': update_list
        }
        if count == 1:
            follower = FoiRequestFollower.objects.get(
                email=email or '', user=user, confirmed=True
            )
            context.update(
                follower.get_context()
            )
        if batch:
            mail_intent = batch_update_follower_email
        else:
            mail_intent = update_follower_email

        mail_intent.send(
            user=user,
            email=email,
            context=context
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
    timestamp = models.DateTimeField(
        _("Timestamp of Following"),
        default=timezone.now
    )
    context = JSONField(blank=True, null=True)

    objects = FoiRequestFollowerManager()

    followed = Signal(providing_args=[])
    unfollowing = Signal(providing_args=[])

    class Meta:
        get_latest_by = 'timestamp'
        ordering = ('-timestamp',)
        verbose_name = _('Request Follower')
        verbose_name_plural = _('Request Followers')
        constraints = [
            models.UniqueConstraint(
                fields=['request', 'user'],
                condition=models.Q(user__isnull=False),
                name='unique_user_follower'
            ),
            models.UniqueConstraint(
                fields=['request', 'email'],
                condition=models.Q(user__isnull=True),
                name='unique_email_follower'
            ),
        ]

    def __str__(self):
        return _("%(user)s follows %(request)s") % {
                "user": self.email or str(self.user),
                "request": self.request}

    def get_context(self):
        return {
            'unsubscribe_url': self.get_unfollow_link(),
            'unsubscribe_reference': '{prefix}{pk}'.format(
                prefix=REFERENCE_PREFIX, pk=self.id
            )
        }

    def get_unfollow_link(self, user=None):
        return self.get_link(kind="unfollow", user=user)

    def get_follow_link(self, user=None):
        return self.get_link(user=user)

    def get_link(self, kind="follow", user=user):
        url = reverse(
            'foirequestfollower-confirm_%s' % kind,
            kwargs={
                'follow_id': self.id,
                'check': self.get_follow_secret()
            }
        )
        if user is not None:
            return user.get_autologin_url(url)
        return settings.SITE_URL + url

    def get_follow_secret(self):
        to_sign = [self.email, str(self.request.id), str(self.id)]
        return hmac.new(
            settings.SECRET_KEY.encode('utf-8'),
            (".".join(to_sign)).encode('utf-8')
        ).hexdigest()

    def check_and_unfollow(self, check):
        secret = self.get_follow_secret()
        if constant_time_compare(check, secret):
            FoiRequestFollower.unfollowing.send(sender=self)
            self.delete()
            return True
        return False

    def check_and_follow(self, check):
        secret = self.get_follow_secret()
        if constant_time_compare(check, secret):
            if self.confirmed:
                return True
            if self.email:
                user = FoiRequestFollower.objects.get_user_for_email(
                    self.email
                )
                if user is not None and user.id != self.request_id:
                    self.user = user
                    self.email = ''
            self.confirmed = True
            self.save()
            FoiRequestFollower.followed.send(sender=self)
            return True
        return False

    def send_confirm_follow_mail(self, extra_data, user=None):
        '''
        user is unconfirmed, but matches email address if given
        '''
        context = {
            "foirequest": self.request,
            "user": user,
            "action_url": self.get_follow_link(user=user),
        }
        context.update(extra_data)
        context.update(self.get_context())
        follow_request_email.send(
            email=self.email,
            subject=_('Please confirm notifications for request “{title}”').format(
                title=self.request.title
            ),
            context=context,
            priority=True
        )
