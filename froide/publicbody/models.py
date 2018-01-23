# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from datetime import timedelta

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.urls import reverse
from django.conf import settings
from django.utils.text import Truncator
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible

from taggit.managers import TaggableManager
from taggit.models import TagBase, ItemBase
from taggit.utils import edit_string_for_tags
from treebeard.mp_tree import MP_Node, MP_NodeManager

from froide.helper.date_utils import (
    calculate_workingday_range,
    calculate_month_range_de
)
from froide.helper.templatetags.markup import markdown
from froide.helper.csv_utils import export_csv


class JurisdictionManager(models.Manager):
    def get_visible(self):
        return self.get_queryset()\
                .filter(hidden=False).order_by('rank', 'name')

    def get_list(self):
        return self.get_visible().annotate(num_publicbodies=models.Count('publicbody'))


@python_2_unicode_compatible
class Jurisdiction(models.Model):
    name = models.CharField(_("Name"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    hidden = models.BooleanField(_("Hidden"), default=False)
    rank = models.SmallIntegerField(default=1)

    objects = JurisdictionManager()

    class Meta:
        verbose_name = _("Jurisdiction")
        verbose_name_plural = _("Jurisdictions")
        ordering = ('rank', 'name',)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('publicbody-show_jurisdiction',
            kwargs={'slug': self.slug})

    def get_absolute_domain_url(self):
        return "%s%s" % (settings.SITE_URL, self.get_absolute_url())


@python_2_unicode_compatible
class FoiLaw(models.Model):
    name = models.CharField(_("Name"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    long_description = models.TextField(_("Website Text"), blank=True)
    created = models.DateField(_("Creation Date"), blank=True, null=True)
    updated = models.DateField(_("Updated Date"), blank=True, null=True)
    request_note = models.TextField(_("request note"), blank=True)
    meta = models.BooleanField(_("Meta Law"), default=False)
    combined = models.ManyToManyField('FoiLaw', verbose_name=_("Combined Laws"), blank=True)
    letter_start = models.TextField(_("Start of Letter"), blank=True)
    letter_end = models.TextField(_("End of Letter"), blank=True)
    jurisdiction = models.ForeignKey(Jurisdiction, verbose_name=_('Jurisdiction'),
            null=True, on_delete=models.SET_NULL, blank=True)
    priority = models.SmallIntegerField(_("Priority"), default=3)
    url = models.CharField(_("URL"), max_length=255, blank=True)
    max_response_time = models.IntegerField(_("Maximal Response Time"),
            null=True, blank=True, default=30)
    max_response_time_unit = models.CharField(_("Unit of Response Time"),
            blank=True, max_length=32, default='day',
            choices=(('day', _('Day(s)')),
                ('working_day', _('Working Day(s)')),
                ('month_de', _('Month(s) (DE)')),
            ))
    refusal_reasons = models.TextField(
            _("Possible Refusal Reasons, one per line, e.g §X.Y: Privacy Concerns"),
            blank=True)
    mediator = models.ForeignKey('PublicBody', verbose_name=_("Mediator"),
            null=True, blank=True,
            default=None, on_delete=models.SET_NULL,
            related_name="mediating_laws")
    email_only = models.BooleanField(_('E-Mail only'), default=False)
    site = models.ForeignKey(Site, verbose_name=_("Site"),
            null=True, on_delete=models.SET_NULL,
            default=settings.SITE_ID)

    class Meta:
        verbose_name = _("Freedom of Information Law")
        verbose_name_plural = _("Freedom of Information Laws")

    def __str__(self):
        return "%s (%s)" % (self.name, self.jurisdiction)

    def get_absolute_url(self):
        return reverse('publicbody-foilaw-show', kwargs={'slug': self.slug})

    def get_absolute_domain_url(self):
        return "%s%s" % (settings.SITE_URL, self.get_absolute_url())

    @property
    def request_note_html(self):
        return markdown(self.request_note)

    @property
    def description_html(self):
        return markdown(self.description)

    def get_refusal_reason_choices(self):
        not_applicable = [('n/a', _("No law can be applied"))]
        if self.meta:
            return (not_applicable +
                    [(l[0], "%s: %s" % (law.name, l[1]))
                    for law in self.combined.all()
                    for l in law.get_refusal_reason_choices()[1:]])
        else:
            return (not_applicable +
                    [(x, Truncator(x).words(12))
                    for x in self.refusal_reasons.splitlines()])

    @classmethod
    def get_default_law(cls, pb=None):
        if pb:
            try:
                return pb.laws.all().order_by('-meta')[0]
            except IndexError:
                pass
            try:
                return cls.objects.filter(jurisdiction=pb.jurisdiction).order_by('-meta')[0]
            except IndexError:
                pass
        try:
            return FoiLaw.objects.get(id=settings.FROIDE_CONFIG.get("default_law", 1))
        except FoiLaw.DoesNotExist:
            return None

    def as_data(self):
        return {
            "id": self.id, "name": self.name,
            "description_html": self.description_html,
            "request_note_html": self.request_note_html,
            "description": self.description,
            "letter_start": self.letter_start,
            "letter_end": self.letter_end,
            "jurisdiction": self.jurisdiction.name if self.jurisdiction else '',
            "jurisdiction_id": (self.jurisdiction.id
                                if self.jurisdiction else None),
            "email_only": self.email_only
        }

    def calculate_due_date(self, date=None, value=None):
        if date is None:
            date = timezone.now()
        if value is None:
            value = self.max_response_time
        if self.max_response_time_unit == "month_de":
            return calculate_month_range_de(date, value)
        elif self.max_response_time_unit == "day":
            return date + timedelta(days=value)
        elif self.max_response_time_unit == "working_day":
            return calculate_workingday_range(date, value)


class PublicBodyTagManager(models.Manager):
    def get_topic_list(self):
        return (self.get_queryset().filter(is_topic=True)
            .order_by('rank', 'name')
            .annotate(num_publicbodies=models.Count('publicbodies'))
        )


class PublicBodyTag(TagBase):
    is_topic = models.BooleanField(_('as topic'), default=False)
    rank = models.SmallIntegerField(_('rank'), default=0)

    objects = PublicBodyTagManager()

    class Meta:
        verbose_name = _("Public Body Tag")
        verbose_name_plural = _("Public Body Tags")


class TaggedPublicBody(ItemBase):
    tag = models.ForeignKey(PublicBodyTag, on_delete=models.CASCADE,
                            related_name="publicbodies")
    content_object = models.ForeignKey('PublicBody', on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Tagged Public Body')
        verbose_name_plural = _('Tagged Public Bodies')

    @classmethod
    def tags_for(cls, model, instance=None):
        if instance is not None:
            return cls.tag_model().objects.filter(**{
                '%s__content_object' % cls.tag_relname(): instance
            })
        return cls.tag_model().objects.filter(**{
            '%s__content_object__isnull' % cls.tag_relname(): False
        }).distinct()


class CategoryManager(MP_NodeManager):
    def get_category_list(self):
        count = models.Count('categorized_publicbodies')
        return (self.get_queryset().filter(depth=1, is_topic=True)
            .order_by('name')
            .annotate(num_publicbodies=count)
        )


class Category(TagBase, MP_Node):
    is_topic = models.BooleanField(_('as topic'), default=False)

    node_order_by = ['name']
    objects = CategoryManager()

    class Meta:
        verbose_name = _("category")
        verbose_name_plural = _("categories")

    def save(self, *args, **kwargs):
        if self.pk is None and kwargs.get('force_insert'):
            obj = Category.add_root(
                name=self.name,
                slug=self.slug,
                is_topic=self.is_topic
            )
            self.pk = obj.pk
        else:
            TagBase.save(self, *args, **kwargs)


class CategorizedPublicBody(ItemBase):
    tag = models.ForeignKey(Category, on_delete=models.CASCADE,
                            related_name="categorized_publicbodies")
    content_object = models.ForeignKey('PublicBody', on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Categorized Public Body')
        verbose_name_plural = _('Categorized Public Bodies')

    @classmethod
    def tags_for(cls, model, instance=None):
        if instance is not None:
            return cls.tag_model().objects.filter(**{
                '%s__content_object' % cls.tag_relname(): instance
            })
        return cls.tag_model().objects.filter(**{
            '%s__content_object__isnull' % cls.tag_relname(): False
        }).distinct()


@python_2_unicode_compatible
class Classification(MP_Node):
    name = models.CharField(_("name"), max_length=255)
    slug = models.SlugField(_("slug"), max_length=255)

    node_order_by = ['name']

    class Meta:
        verbose_name = _("classification")
        verbose_name_plural = _("classifications")

    def __str__(self):
        return self.name


class PublicBodyManager(CurrentSiteManager):
    def get_queryset(self):
        return (super(PublicBodyManager, self).get_queryset()
                .exclude(email='')
                .filter(email__isnull=False)
        )

    def get_list(self):
        return self.get_queryset()\
            .filter(jurisdiction__hidden=False)\
            .select_related('jurisdiction')

    def get_for_search_index(self):
        return self.get_queryset()


@python_2_unicode_compatible
class PublicBody(models.Model):
    name = models.CharField(_("Name"), max_length=255)
    other_names = models.TextField(_("Other names"), default="", blank=True)
    slug = models.SlugField(_("Slug"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    url = models.URLField(_("URL"), null=True, blank=True, max_length=500)

    parent = models.ForeignKey('PublicBody', null=True, blank=True,
            default=None, on_delete=models.SET_NULL,
            related_name="children")
    root = models.ForeignKey('PublicBody', null=True, blank=True,
            default=None, on_delete=models.SET_NULL,
            related_name="descendants")
    depth = models.SmallIntegerField(default=0)

    classification = models.ForeignKey(Classification, null=True, blank=True,
        on_delete=models.SET_NULL)

    email = models.EmailField(_("Email"), null=True, blank=True)
    contact = models.TextField(_("Contact"), blank=True)
    address = models.TextField(_("Address"), blank=True)
    website_dump = models.TextField(_("Website Dump"), null=True, blank=True)
    request_note = models.TextField(_("request note"), blank=True)

    file_index = models.CharField(_("file index"), max_length=1024, blank=True)
    org_chart = models.CharField(_("organisational chart"), max_length=1024, blank=True)

    _created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
            verbose_name=_("Created by"),
            blank=True, null=True, related_name='public_body_creators',
            on_delete=models.SET_NULL)
    _updated_by = models.ForeignKey(settings.AUTH_USER_MODEL,
            verbose_name=_("Updated by"),
            blank=True, null=True, related_name='public_body_updaters',
            on_delete=models.SET_NULL)
    created_at = models.DateTimeField(_("Created at"), default=timezone.now)
    updated_at = models.DateTimeField(_("Updated at"), default=timezone.now)
    confirmed = models.BooleanField(_("confirmed"), default=True)

    number_of_requests = models.IntegerField(_("Number of requests"),
            default=0)
    site = models.ForeignKey(Site, verbose_name=_("Site"),
            null=True, on_delete=models.SET_NULL, default=settings.SITE_ID)

    jurisdiction = models.ForeignKey(Jurisdiction, verbose_name=_('Jurisdiction'),
            blank=True, null=True, on_delete=models.SET_NULL)

    laws = models.ManyToManyField(FoiLaw,
            verbose_name=_("Freedom of Information Laws"))
    tags = TaggableManager(through=TaggedPublicBody, blank=True)
    categories = TaggableManager(
        through=CategorizedPublicBody,
        verbose_name=_("categories"),
        blank=True
    )

    non_filtered_objects = models.Manager()
    objects = PublicBodyManager()
    published = objects

    class Meta:
        ordering = ('name',)
        verbose_name = _("Public Body")
        verbose_name_plural = _("Public Bodies")

    serializable_fields = ('id', 'name', 'slug', 'request_note_html',
            'description', 'url', 'email', 'contact',
            'address', 'domain', 'number_of_requests')

    def __str__(self):
        return "%s (%s)" % (self.name, self.jurisdiction)

    @property
    def created_by(self):
        return self._created_by

    @property
    def updated_by(self):
        return self._updated_by

    @property
    def domain(self):
        if self.url and self.url.count('/') > 1:
            return self.url.split("/")[2]
        return None

    @property
    def all_names(self):
        names = [self.name, self.other_names]
        if self.jurisdiction:
            names.extend([self.jurisdiction.name, self.jurisdiction.slug])
        return ' '.join(names)

    @property
    def request_note_html(self):
        return markdown(self.request_note)

    @property
    def tag_list(self):
        return edit_string_for_tags(self.tags.all())

    @property
    def default_law(self):
        return FoiLaw.get_default_law(self)

    def get_absolute_url(self):
        return reverse('publicbody-show', kwargs={"slug": self.slug})

    def get_absolute_domain_url(self):
        return "%s%s" % (settings.SITE_URL, self.get_absolute_url())

    def get_mediator(self):
        law = self.default_law
        if law is None:
            return None
        return law.mediator

    def get_label(self):
        return mark_safe('%(name)s - <a href="%(url)s" target="_blank" class="info-link">%(detail)s</a>' % {"name": escape(self.name), "url": self.get_absolute_url(), "detail": _("More Info")})

    def confirm(self):
        if self.confirmed:
            return None
        self.confirmed = True
        self.save()
        counter = 0
        for request in self.foirequest_set.all():
            if request.confirmed_public_body():
                counter += 1
        return counter

    def as_data(self):
        d = {}
        for field in self.serializable_fields:
            d[field] = getattr(self, field)
        d['default_law'] = self.default_law.as_data()
        d['jurisdiction'] = {
            'name': self.jurisdiction.name,
            'id': self.jurisdiction.id
        }
        return d

    def as_json(self):
        return json.dumps(self.as_data())

    @property
    def children_count(self):
        return len(PublicBody.objects.filter(parent=self))

    @classmethod
    def export_csv(cls, queryset):
        fields = ("id", "name", "email", "contact",
            "address", "url", "classification",
            "jurisdiction__slug", "tags",
            "other_names", "website_dump", "description",
            "request_note", "parent__name",
        )

        return export_csv(queryset, fields)
