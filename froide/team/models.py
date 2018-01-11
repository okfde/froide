from __future__ import unicode_literals

from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class TeamMembership(models.Model):
    ROLE_OWNER = 'owner'
    ROLE_EDITOR = 'editor'
    ROLE_VIEWER = 'viewer'
    ROLES = (
        (ROLE_OWNER, _('owner')),
        (ROLE_EDITOR, _('editor')),
        (ROLE_VIEWER, _('viewer')),
    )
    MEMBERSHIP_STATUS_INACTIVE = 'inactive'
    MEMBERSHIP_STATUS_INVITED = 'invited'
    MEMBERSHIP_STATUS_ACTIVE = 'active'
    MEMBERSHIP_STATUS = (
        (MEMBERSHIP_STATUS_INACTIVE, _('inactive')),
        (MEMBERSHIP_STATUS_INVITED, _('invited')),
        (MEMBERSHIP_STATUS_ACTIVE, _('active')),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.CASCADE)
    email = models.CharField(max_length=255, blank=True)
    team = models.ForeignKey('Team', on_delete=models.CASCADE)
    role = models.CharField(max_length=30, choices=ROLES)
    status = models.CharField(max_length=30, choices=MEMBERSHIP_STATUS)
    created = models.DateTimeField(default=timezone.now)
    updated = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return '%s in %s' % (self.user, self.team)

    def is_active(self):
        return self.status == self.MEMBERSHIP_STATUS_ACTIVE

    def is_invited(self):
        return self.status == self.MEMBERSHIP_STATUS_INVITED

    def is_owner(self):
        return self.role == self.ROLE_OWNER

    def send_invite_mail(self):
        pass


@python_2_unicode_compatible
class Team(models.Model):
    name = models.CharField(max_length=255)
    created = models.DateTimeField(default=timezone.now)

    members = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                     through=TeamMembership)

    class Meta:
        verbose_name = _('team')
        verbose_name_plural = _('teams')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('team-detail', kwargs={'pk': self.pk})

    @property
    def member_count(self):
        return self.members.count()

    def get_invite_form(self):
        pass
