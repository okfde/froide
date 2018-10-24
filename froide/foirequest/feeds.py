import re

from django.conf import settings
from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse
from django.shortcuts import get_object_or_404

from .models import FoiRequest
from .filters import FOIREQUEST_FILTER_DICT

CONTROLCHARS_RE = re.compile(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]')


def clean(val):
    return CONTROLCHARS_RE.sub('', val)


class LatestFoiRequestsFeed(Feed):
    url_name = 'foirequest-list_feed'

    def __init__(self, items, data, make_url):
        self.items = items
        self.data = data
        self.make_url = make_url
        super(LatestFoiRequestsFeed, self).__init__()

    def get_filter_string(self):
        by = []
        if self.data.get('q'):
            by.append(_('search for "%s"' % self.data['q']))
        if self.data.get('category'):
            by.append(_('by category %(category)s') % {'category': self.data['category'].name})
        if self.data.get('status'):
            by.append(_('by status %(status)s') % {
                'status': FOIREQUEST_FILTER_DICT[self.filter_obj['status']][1]
            })
        if self.data.get('tag'):
            by.append(_('by tag %(tag)s') % {'tag': self.data['tag'].name})
        if self.data.get('jurisdiction'):
            by.append(_('for %(juris)s') % {'juris': self.data['jurisdiction'].name})
        if self.data.get('publicbody'):
            by.append(_('to %(publicbody)s') % {'publicbody': self.data['publicbody'].name})
        return ' '.join(str(x) for x in by)

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

    def link(self):
        return self.make_url(self.url_name)

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
    url_name = 'foirequest-list_feed_atom'


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
