# -*- coding: utf-8 -*-
import json
from datetime import timedelta

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.utils.text import Truncator
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.utils import timezone

from froide.helper.date_utils import (calculate_workingday_range,
        calculate_month_range_de)
from froide.helper.templatetags.markup import markdown
from froide.helper.form_generator import FormGenerator


class JurisdictionManager(models.Manager):
    def get_visible(self):
        return super(JurisdictionManager, self).get_query_set()\
                .filter(hidden=False).order_by('rank', 'name')


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

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('publicbody-show_jurisdiction',
            kwargs={'slug': self.slug})

    def get_absolute_domain_url(self):
        return u"%s%s" % (settings.SITE_URL, self.get_absolute_url())


class PublicBodyManager(CurrentSiteManager):
    def get_query_set(self):
        return super(PublicBodyManager, self).get_query_set()\
                .exclude(email="")\
                .filter(email__isnull=False)

    def get_list(self):
        return self.get_query_set()\
            .filter(jurisdiction__hidden=False)

    def get_for_homepage(self, count=5):
        return self.get_query_set().order_by('-number_of_requests')[:count]

    def get_for_search_index(self):
        return self.get_query_set()


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
            _(u"Possible Refusal Reasons, one per line, e.g §X.Y: Privacy Concerns"),
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

    def __unicode__(self):
        return u"%s (%s)" % (self.name, self.jurisdiction)

    def get_absolute_url(self):
        return reverse('publicbody-foilaw-show', kwargs={'slug': self.slug})

    def get_absolute_domain_url(self):
        return u"%s%s" % (settings.SITE_URL, self.get_absolute_url())

    @property
    def formatted_description(self):
        return markdown(self.description)

    @property
    def letter_start_form(self):
        return mark_safe(FormGenerator(self.letter_start).render_html())

    @property
    def letter_end_form(self):
        return mark_safe(FormGenerator(self.letter_end).render_html())

    def get_letter_start_text(self, post):
        return FormGenerator(self.letter_start, post).render()

    def get_letter_end_text(self, post):
        return FormGenerator(self.letter_end, post).render()

    @property
    def request_note_markdown(self):
        return markdown(self.request_note)

    def get_refusal_reason_choices(self):
        not_applicable = [(_("Law not applicable"), _("No law can be applied"))]
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
            return cls.objects.filter(jurisdiction=pb.jurisdiction).order_by('-meta')[0]
        try:
            return FoiLaw.objects.get(id=settings.FROIDE_CONFIG.get("default_law", 1))
        except FoiLaw.DoesNotExist:
            raise ImproperlyConfigured(u'You need to setup a default FoiLaw object and reference id in settings')

    def as_dict(self):
        return {
            "pk": self.pk, "name": self.name,
            "description_markdown": markdown(self.description),
            "request_note_markdown": self.request_note_markdown,
            "description": self.description,
            "letter_start": self.letter_start,
            "letter_end": self.letter_end,
            "letter_start_form": self.letter_start_form,
            "letter_end_form": self.letter_end_form,
            "jurisdiction": self.jurisdiction.name,
            "jurisdiction_id": self.jurisdiction.id,
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


class PublicBodyTopicManager(models.Manager):
    def get_list(self):
        return list(self.get_query_set().order_by("rank", "name"))


class PublicBodyTopic(models.Model):
    name = models.CharField(_("Name"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    count = models.IntegerField(_("Count"), default=0)
    rank = models.IntegerField(_("Rank"), default=0)

    objects = PublicBodyTopicManager()

    class Meta:
        verbose_name = _("Topic")
        verbose_name_plural = _("Topics")

    def __unicode__(self):
        return self.name


class PublicBody(models.Model):
    name = models.CharField(_("Name"), max_length=255)
    other_names = models.TextField(_("Other names"), default="", blank=True)
    slug = models.SlugField(_("Slug"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    topic = models.ForeignKey(PublicBodyTopic, verbose_name=_("Topic"),
            null=True, on_delete=models.SET_NULL)
    url = models.URLField(_("URL"), null=True, blank=True, max_length=500)
    parent = models.ForeignKey('PublicBody', null=True, blank=True,
            default=None, on_delete=models.SET_NULL,
            related_name="children")
    root = models.ForeignKey('PublicBody', null=True, blank=True,
            default=None, on_delete=models.SET_NULL,
            related_name="descendants")
    depth = models.SmallIntegerField(default=0)
    classification = models.CharField(_("Classification"), max_length=255,
            blank=True)
    classification_slug = models.SlugField(_("Classification Slug"), max_length=255)

    email = models.EmailField(_("Email"), null=True, blank=True)
    contact = models.TextField(_("Contact"), blank=True)
    address = models.TextField(_("Address"), blank=True)
    website_dump = models.TextField(_("Website Dump"), null=True, blank=True)
    request_note = models.TextField(_("request note"), blank=True)

    _created_by = models.ForeignKey(User, verbose_name=_("Created by"),
            blank=True, null=True, related_name='public_body_creators',
            on_delete=models.SET_NULL, default=1)
    _updated_by = models.ForeignKey(User, verbose_name=_("Updated by"),
            blank=True, null=True, related_name='public_body_updaters',
            on_delete=models.SET_NULL, default=1)
    confirmed = models.BooleanField(_("confirmed"), default=True)

    number_of_requests = models.IntegerField(_("Number of requests"),
            default=0)
    site = models.ForeignKey(Site, verbose_name=_("Site"),
            null=True, on_delete=models.SET_NULL, default=settings.SITE_ID)

    jurisdiction = models.ForeignKey(Jurisdiction, verbose_name=_('Jurisdiction'),
            blank=True, null=True, on_delete=models.SET_NULL)

    laws = models.ManyToManyField(FoiLaw,
            verbose_name=_("Freedom of Information Laws"))

    non_filtered_objects = models.Manager()
    objects = PublicBodyManager()
    published = objects

    class Meta:
        ordering = ('name',)
        verbose_name = _("Public Body")
        verbose_name_plural = _("Public Bodies")

    serializable_fields = ('name', 'slug', 'request_note_markdown',
            'description', 'topic_name', 'url', 'email', 'contact',
            'address', 'domain')

    def __unicode__(self):
        return u"%s (%s)" % (self.name, self.jurisdiction)

    @property
    def created_by(self):
        return self._created_by or AnonymousUser()

    @property
    def updated_by(self):
        return self._updated_by or AnonymousUser()

    @property
    def domain(self):
        if self.url:
            return self.url.split("/")[2]
        return None

    @property
    def topic_name(self):
        if self.topic:
            return self.topic.name
        return None

    @property
    def request_note_markdown(self):
        return markdown(self.request_note)

    @property
    def default_law(self):
        return FoiLaw.get_default_law(self)

    def get_absolute_url(self):
        return reverse('publicbody-show', kwargs={"slug": self.slug})

    def get_absolute_domain_url(self):
        return u"%s%s" % (settings.SITE_URL, self.get_absolute_url())

    def get_label(self):
        return mark_safe('%(name)s - <a href="%(url)s" class="target-new info-link">%(detail)s</a>' % {"name": escape(self.name), "url": self.get_absolute_url(), "detail": _("More Info")})

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

    def as_json(self):
        d = {}
        for field in self.serializable_fields:
            d[field] = getattr(self, field)
        d['laws'] = [self.default_law.as_dict()]
        d['jurisdiction'] = self.jurisdiction.name
        return json.dumps(d)

    @property
    def children_count(self):
        return len(PublicBody.objects.filter(parent=self))

    @classmethod
    def export_csv(cls, queryset):
        import unicodecsv
        from StringIO import StringIO

        s = StringIO()
        fields = ("id", "name", "email", "contact",
            "address", "url", "classification",
            "jurisdiction__slug", "topic__slug",
            "other_names", "website_dump", "description",
            "request_note", "parent__name",
        )

        writer = unicodecsv.DictWriter(s, fields, encoding='utf-8')
        writer.writerow(dict([(v, v) for v in fields]))
        for pb in queryset:
            d = {}
            for field in fields:
                value = pb
                for f in field.split('__'):
                    value = getattr(value, f)
                    if value is None:
                        break
                if value is None:
                    d[field] = ""
                else:
                    d[field] = value
            writer.writerow(d)

        s.seek(0)
        return s.read()
