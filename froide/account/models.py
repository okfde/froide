import hmac

from django.db import models
from django.conf import settings
from django import dispatch
from django.utils.translation import ugettext as _
from django.db.models.signals import post_save
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.contrib.auth.models import User

from mailer import send_mail


@dispatch.receiver(post_save, sender=User)
def create_profile(sender, instance=None, created=False, **kwargs):
    if created or instance.get_profile() is None:
        Profile.objects.create(user=instance)

user_activated_signal = dispatch.Signal(providing_args=[])


class Profile(models.Model):
    user = models.OneToOneField(User)


class AccountManager(object):
    def __init__(self, user):
        self.user = user

    @classmethod
    def get_username_base(self, firstname, lastname):
        base = u""
        first = slugify(firstname)
        last = slugify(lastname)
        if first and last:
            base = u"%s.%s" % (first[0], last)
        elif last:
            base = last
        elif first:
            base = first
        else:
            base = u"user"
        return base

    def confirm_account(self, secret, request_id=None):
        if not self.check_confirmation_secret(secret, request_id):
            return
        self.user.is_active = True
        self.user.save()
        user_activated_signal.send_robust(sender=self.user)
        return self.user


    def check_confirmation_secret(self, secret, request_id):
        return self.generate_confirmation_secret(request_id) == secret

    def generate_confirmation_secret(self, request_id=None):
        to_sign = [str(self.user.pk), self.user.email]
        if request_id is not None:
            to_sign.append(str(request_id))
        if self.user.last_login:
            to_sign.append(str(self.user.last_login))
        return hmac.new(settings.SECRET_KEY, ".".join(to_sign)).hexdigest()

    def send_confirmation_mail(self, request_id=None, password=None):
        secret = self.generate_confirmation_secret(request_id)
        url_kwargs = {"user_id": self.user.pk, "secret": secret}
        if request_id:
            url_kwargs['request_id'] = request_id
        url = reverse('account-confirm', kwargs=url_kwargs)
        message = render_to_string('account/confirmation_mail.txt',
                {'url': settings.SITE_URL + url,
                'password': password,
                'name': self.user.get_full_name(),
                'site_name': settings.SITE_NAME,
                'site_url': settings.SITE_URL
            })
        send_mail(_("%s: please confirm your account" % settings.SITE_NAME),
                message, settings.DEFAULT_FROM_EMAIL, [self.user.email])

    @classmethod
    def create_user(cls, **data):
        user = User(first_name=data['first_name'],
                last_name=data['last_name'],
                email=data['email'])
        username_base = cls.get_username_base(user.first_name, user.last_name)
        count = 0
        while True:
            if count:
                username = "%s_%s" % (username_base, count)
            else:
                username = username_base
            try:
                User.objects.get(username=username)
            except User.DoesNotExist:
                break
            count += 1
        user.username = username
        user.is_active = False
        if "password" in data:
            password = data['password']
        else:
            password = User.objects.make_random_password()
        user.set_password(password)
        user.save()
        return user, password
