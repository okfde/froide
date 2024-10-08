import os

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from froide.helper.fields import SVGAndImageField
from froide.helper.storage import HashedFilenameStorage


class OrganizationRole(models.TextChoices):
    OWNER = "owner", _("owner")
    MEMBER = "member", _("member")


class OrganizationMembershipStatus(models.TextChoices):
    INACTIVE = "inactive", _("inactive")
    INVITED = "invited", _("invited")
    ACTIVE = "active", _("active")


class OrganizationMembership(models.Model):
    ROLE = OrganizationRole
    ROLES_DICT = dict(OrganizationRole.choices)
    STATUS = OrganizationMembershipStatus

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    email = models.CharField(max_length=255, blank=True)
    organization = models.ForeignKey("Organization", on_delete=models.CASCADE)
    role = models.CharField(max_length=30, choices=OrganizationRole.choices)
    status = models.CharField(
        max_length=30, choices=OrganizationMembershipStatus.choices
    )
    created = models.DateTimeField(default=timezone.now)
    updated = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization"],
                condition=models.Q(user__isnull=False),
                name="unique_user_organization",
            )
        ]

    def __str__(self):
        return "%s in %s" % (self.user, self.organization)

    def is_active(self):
        return self.status == self.STATUS.ACTIVE

    def is_invited(self):
        return self.status == self.STATUS.INVITED

    def is_owner(self):
        return self.role == self.ROLE.OWNER


def logo_path(instance=None, filename=None):
    path = ["orglogo", filename]
    return os.path.join(*path)


class OrganizationManager(models.Manager):
    def get_by_email(self, email):
        email_domain = email.split("@")[-1]
        return Organization.objects.filter(email_domain=email_domain).first()

    def get_owner_organizations(self, user, *args, **kwargs):
        return self.get_for_user(
            user,
            organizationmembership__role=OrganizationMembership.ROLE.OWNER,
        )

    def get_for_user(self, user, *args, **kwargs):
        return self.get_queryset().filter(
            *args,
            organizationmembership__user=user,
            organizationmembership__status=OrganizationMembership.STATUS.ACTIVE,
            **kwargs,
        )

    def get_public(self):
        return self.get_queryset().filter(show_in_list=True)


class Organization(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    website = models.URLField(blank=True)
    created = models.DateTimeField(default=timezone.now)
    description = models.TextField(blank=True)

    email_domain = models.CharField(max_length=255, blank=True)

    logo = SVGAndImageField(
        null=True,
        blank=True,
        upload_to=logo_path,
        storage=HashedFilenameStorage(),
    )
    show_in_list = models.BooleanField()

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through=OrganizationMembership,
    )

    objects = OrganizationManager()

    class Meta:
        verbose_name = _("organization")
        verbose_name_plural = _("organizations")

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.active_memberships.count()

    @property
    def active_memberships(self):
        return OrganizationMembership.objects.filter(
            organization=self, status=OrganizationMembershipStatus.ACTIVE
        )

    def add_user(
        self,
        user,
        role=OrganizationMembership.ROLE.MEMBER,
        status=OrganizationMembership.STATUS.ACTIVE,
    ):
        if OrganizationMembership.objects.filter(user=user, organization=self).exists():
            return False
        OrganizationMembership.objects.create(
            user=user, organization=self, role=role, status=status
        )

    def get_absolute_url(self):
        return reverse("organization-detail", kwargs={"slug": self.slug})

    def get_role_display(self):
        if hasattr(self, "role"):
            return OrganizationMembership.ROLES_DICT[self.role]
        return ""
