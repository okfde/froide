from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .category import Category
from .publicbody import PublicBody


class PublicBodyContactManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(confirmed=True)

    def get_alternative_emails(self):
        return (
            self.get_queryset()
            .exclude(email="")
            .exclude(category__isnull=True)
            .only(
                "email",
            )
            .annotate(category_name=models.F("category__name"))
        )


class PublicBodyContact(models.Model):
    publicbody = models.ForeignKey(
        PublicBody, on_delete=models.CASCADE, related_name="contacts"
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="public_body_contacts",
    )
    confirmed = models.BooleanField(_("confirmed"), default=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    email = models.EmailField(_("Email"), blank=True, default="")
    fax = models.CharField(_("Fax"), max_length=50, blank=True, default="")

    class Meta:
        verbose_name = _("Public Body Contact")
        verbose_name_plural = _("Public Body Contacts")
        constraints = [
            models.UniqueConstraint(
                fields=["publicbody", "category"],
                condition=models.Q(confirmed=True),
                name="unique_publicbody_category",
            ),
            models.UniqueConstraint(
                fields=["publicbody", "category", "user"],
                condition=models.Q(confirmed=False),
                name="unique_publicbody_category_draft",
            ),
        ]

    non_filtered_objects = models.Manager()
    objects = PublicBodyContactManager()

    def __str__(self):
        return "{}: {} ({})".format(self.publicbody, self.category, self.email)


class ProposedPublicBodyContactManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(confirmed=False)


class ProposedPublicBodyContact(PublicBodyContact):
    objects = ProposedPublicBodyContactManager()

    class Meta:
        proxy = True
        verbose_name = _("Proposed Public Body Contact")
        verbose_name_plural = _("Proposed Public Body Contacts")
