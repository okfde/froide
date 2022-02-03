from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class TeamMembership(models.Model):
    ROLE_OWNER = "owner"
    ROLE_EDITOR = "editor"
    ROLE_VIEWER = "viewer"
    ROLES = (
        (ROLE_OWNER, _("owner")),
        (ROLE_EDITOR, _("editor")),
        (ROLE_VIEWER, _("viewer")),
    )
    ROLES_DICT = dict(ROLES)
    MEMBERSHIP_STATUS_INACTIVE = "inactive"
    MEMBERSHIP_STATUS_INVITED = "invited"
    MEMBERSHIP_STATUS_ACTIVE = "active"
    MEMBERSHIP_STATUS = (
        (MEMBERSHIP_STATUS_INACTIVE, _("inactive")),
        (MEMBERSHIP_STATUS_INVITED, _("invited")),
        (MEMBERSHIP_STATUS_ACTIVE, _("active")),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE
    )
    email = models.CharField(max_length=255, blank=True)
    team = models.ForeignKey("Team", on_delete=models.CASCADE)
    role = models.CharField(max_length=30, choices=ROLES)
    status = models.CharField(max_length=30, choices=MEMBERSHIP_STATUS)
    created = models.DateTimeField(default=timezone.now)
    updated = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "team"],
                condition=models.Q(user__isnull=False),
                name="unique_user_team",
            )
        ]

    def __str__(self):
        return "%s in %s" % (self.user, self.team)

    def is_active(self):
        return self.status == self.MEMBERSHIP_STATUS_ACTIVE

    def is_invited(self):
        return self.status == self.MEMBERSHIP_STATUS_INVITED

    def is_owner(self):
        return self.role == self.ROLE_OWNER

    def send_invite_mail(self):
        pass


class TeamManager(models.Manager):
    def get_for_user(self, user, *args, **kwargs):
        return self.get_queryset().filter(
            *args,
            teammembership__user=user,
            teammembership__status=TeamMembership.MEMBERSHIP_STATUS_ACTIVE,
            **kwargs
        )

    def get_list_for_user(self, user, *args, **kwargs):
        return list(self.get_for_user(user).values_list("id", flat=True))

    def get_owner_teams(self, user):
        return self.get_for_user(user, teammembership__role=TeamMembership.ROLE_OWNER)

    def get_editor_owner_teams(self, user):
        return self.get_for_user(
            user,
            models.Q(teammembership__role=TeamMembership.ROLE_OWNER)
            | models.Q(teammembership__role=TeamMembership.ROLE_EDITOR),
        )


class Team(models.Model):
    name = models.CharField(max_length=255)
    created = models.DateTimeField(default=timezone.now)

    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through=TeamMembership)

    objects = TeamManager()

    class Meta:
        verbose_name = _("team")
        verbose_name_plural = _("teams")
        permissions = (("can_use_teams", _("Can use teams")),)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("team-detail", kwargs={"pk": self.pk})

    def get_role_display(self):
        if hasattr(self, "role"):
            return TeamMembership.ROLES_DICT[self.role]
        return ""

    @property
    def member_count(self):
        return self.members.count()

    def can_do(self, verb, user):
        if verb == "read":
            return self.can_read(user)
        if verb == "write":
            return self.can_write(user)
        if verb == "manage":
            return self.can_manage(user)
        raise ValueError("Invalid auth verb")

    def _can_do(self, user, *args):
        kwargs = dict(status=TeamMembership.MEMBERSHIP_STATUS_ACTIVE, user=user)
        return self.teammembership_set.filter(*args, **kwargs).exists()

    def can_read(self, user):
        return self._can_do(user)

    def can_write(self, user):
        return self._can_do(
            user,
            models.Q(role=TeamMembership.ROLE_EDITOR)
            | models.Q(role=TeamMembership.ROLE_OWNER),
        )

    def can_manage(self, user):
        return self._can_do(user, models.Q(role=TeamMembership.ROLE_OWNER))
