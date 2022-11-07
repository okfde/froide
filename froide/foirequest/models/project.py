from django.conf import settings
from django.contrib.sites.managers import CurrentSiteManager
from django.contrib.sites.models import Site
from django.db import models
from django.dispatch import Signal
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from taggit.managers import TaggableManager
from taggit.models import TaggedItemBase

from froide.helper.text_utils import redact_plaintext
from froide.publicbody.models import PublicBody
from froide.team.models import Team


class TaggedFoiProject(TaggedItemBase):
    content_object = models.ForeignKey("FoiProject", on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Project Tag")
        verbose_name_plural = _("Project Tags")


class FoiProjectManager(CurrentSiteManager):
    def get_for_user(self, user, **query_kwargs):
        qs = self.get_queryset()
        user_teams = Team.objects.get_for_user(user)
        qs = qs.filter(
            models.Q(user=user) | models.Q(team__in=user_teams), **query_kwargs
        )
        return qs


class FoiProject(models.Model):
    STATUS_PENDING = "pending"
    STATUS_READY = "ready"
    STATUS_COMPLETE = "complete"
    STATUS_ASLEEP = "asleep"

    STATUS_CHOICES = (
        (STATUS_PENDING, _("pending")),
        (STATUS_READY, _("ready")),
        (STATUS_COMPLETE, _("complete")),
        (STATUS_ASLEEP, _("asleep")),
    )

    title = models.CharField(_("Title"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)

    description = models.TextField(_("Description"), blank=True)

    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING
    )

    created = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)

    public = models.BooleanField(_("published?"), default=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_("User"),
    )
    team = models.ForeignKey(
        Team, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("Team")
    )

    request_count = models.IntegerField(default=0)
    reference = models.CharField(_("Reference"), blank=True, max_length=255)
    tags = TaggableManager(through=TaggedFoiProject, blank=True)
    publicbodies = models.ManyToManyField(PublicBody, blank=True)

    language = models.CharField(
        max_length=10,
        blank=True,
        default=settings.LANGUAGE_CODE,
        choices=settings.LANGUAGES,
    )

    site = models.ForeignKey(
        Site, null=True, on_delete=models.SET_NULL, verbose_name=_("Site")
    )

    objects = FoiProjectManager()

    class Meta:
        verbose_name = _("FOI Project")
        verbose_name_plural = _("FOI Projects")
        ordering = ("last_update",)

    project_created = Signal()  # args: []

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("foirequest-project", kwargs={"slug": self.slug})

    def get_absolute_short_url(self):
        return reverse("foirequest-project_shortlink", kwargs={"obj_id": self.id})

    def get_absolute_domain_url(self):
        return "%s%s" % (settings.SITE_URL, self.get_absolute_url())

    def get_absolute_domain_short_url(self):
        return "%s%s" % (settings.SITE_URL, self.get_absolute_short_url())

    def is_public(self):
        return self.public

    def add_requests(self, queryset):
        order_max = self.foirequest_set.all().aggregate(models.Max("project_order"))
        order_max = order_max["project_order__max"]
        if order_max is None:
            order_max = -1
        for req in queryset:
            order_max += 1
            req.project = self
            req.project_order = order_max
            req.save()
            if req.public_body:
                self.publicbodies.add(req.public_body)
        self.request_count = self.foirequest_set.all().count()
        self.save()

    def make_public(self, publish_requests=False, user=None):
        self.public = True
        self.save()
        if not publish_requests:
            return
        for req in self.foirequest_set.all():
            if not req.is_public():
                req.make_public(user=user)

    def recalculate_order(self):
        requests = self.foirequest_set.order_by("project_order").all()
        for i, req in enumerate(requests):
            if req.project != self or req.project_order != i:
                req.project = self
                req.project_order = i
                req.save()

            if req.public_body:
                self.publicbodies.add(req.public_body)

        self.request_count = len(requests)
        self.save()

    def get_description(self):
        user_replacements = self.user.get_redactions()
        return redact_plaintext(self.description, user_replacements=user_replacements)
