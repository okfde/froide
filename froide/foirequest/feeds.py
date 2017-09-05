import re

from django.conf import settings
from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse
from django.shortcuts import get_object_or_404

from .models import FoiRequest

CONTROLCHARS_RE = re.compile(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]')


def clean(val):
    return CONTROLCHARS_RE.sub('', val)


class LatestFoiRequestsFeed(Feed):
    def __init__(self, items, topic=None, jurisdiction=None, public_body=None, tag=None, status=None):
        self.items = items
        self.topic = topic
        self.jurisdiction = jurisdiction
        self.tag = tag
        self.status = status
        self.public_body = public_body
        super(LatestFoiRequestsFeed, self).__init__()

    def get_filter_string(self):
        by = []
        if self.topic:
            by.append(_('by topic %(topic)s') % {'topic': self.topic.name})
        if self.status:
            by.append(_('by status %(status)s') % {
                'status': FoiRequest.get_readable_status(
                    FoiRequest.get_status_from_url(self.status)[1])
            })
        if self.tag:
            by.append(_('by tag %(tag)s') % {'tag': self.tag.name})
        if self.jurisdiction:
            by.append(_('for %(juris)s') % {'juris': self.jurisdiction.name})
        if self.public_body:
            by.append(_('to %(public_body)s') % {'public_body': self.public_body.name})
        return ' '.join(by)

    def title(self, obj):
        by = self.get_filter_string()
        if by:
            return clean(_("Freedom of Information Requests %(by)s on %(sitename)s") % {
                "sitename": settings.SITE_NAME,
                'by': by
            })
        return clean(_("Freedom of Information Requests on %(sitename)s") % {
            "sitename": settings.SITE_NAME
        })

    def description(self, obj):
        by = self.get_filter_string()
        if by:
            return clean(_("This feed contains the Freedom of Information requests %(by)s"
                " that have been made through %(sitename)s.") % {
                    "sitename": settings.SITE_NAME,
                    'by': by
                })
        return clean(_("This feed contains the latest Freedom of Information requests"
            " that have been made through %(sitename)s.") % {
                "sitename": settings.SITE_NAME
            })

    def get_link_kwargs(self):
        kwargs = {}
        if self.topic:
            kwargs['topic'] = self.topic.slug
        if self.jurisdiction:
            kwargs['jurisdiction'] = self.jurisdiction.slug
        if self.status:
            kwargs['status'] = self.status
        if self.tag:
            kwargs['tag'] = self.tag.slug
        if self.public_body:
            kwargs['public_body'] = self.public_body.slug
        return kwargs

    def link(self):
        return reverse('foirequest-list_feed', kwargs=self.get_link_kwargs())

    def items(self):
        return self.items.order_by("-first_message")[:15]

    def item_title(self, item):
        if item.public_body:
            pb_name = item.public_body.name
        else:
            pb_name = _("Not yet known")
        return clean(_("'%(title)s' to %(publicbody)s") % {
            "title": item.title,
            "publicbody": pb_name
        })

    def item_description(self, item):
        return clean(item.description)

    def item_pubdate(self, item):
        return item.first_message


class LatestFoiRequestsFeedAtom(LatestFoiRequestsFeed):
    feed_type = Atom1Feed
    subtitle = LatestFoiRequestsFeed.description

    def link(self):
        return reverse('foirequest-list_feed_atom', kwargs=self.get_link_kwargs())


class FoiRequestFeed(Feed):
    def get_object(self, request, slug):
        return get_object_or_404(FoiRequest, slug=slug, public=True)

    def title(self, obj):
        return clean(obj.title)

    def link(self, obj):
        return reverse('foirequest-feed', kwargs={"slug": obj.slug})

    def description(self, obj):
        return clean(obj.description)

    def items(self, obj):
        return obj.foievent_set.order_by("-timestamp")[:15]

    def item_title(self, item):
        return clean(item.as_text())

    def item_description(self, item):
        return clean(item.as_text())

    def item_pubdate(self, item):
        return item.timestamp


class FoiRequestFeedAtom(FoiRequestFeed):
    feed_type = Atom1Feed
    subtitle = FoiRequestFeed.description

    def link(self, obj):
        return reverse('foirequest-feed_atom', kwargs={"slug": obj.slug})
