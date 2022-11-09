from django.conf import settings
from django.contrib.syndication.views import Feed
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import linebreaksbr
from django.urls import reverse
from django.utils.feedgenerator import Atom1Feed
from django.utils.translation import gettext_lazy as _

from froide.foirequest.models.event import EVENT_DETAILS
from froide.helper.feed_utils import clean_feed_output

from .filters import FOIREQUEST_FILTER_DICT
from .models import FoiRequest


class LatestFoiRequestsFeed(Feed):
    url_name = "foirequest-list_feed"

    def __init__(self, items, data, make_url):
        self.items = items
        self.data = data
        self.make_url = make_url
        super(LatestFoiRequestsFeed, self).__init__()

    def get_filter_string(self):
        by = []
        if self.data.get("q"):
            by.append(_('search for "%s"' % self.data["q"]))
        if self.data.get("category"):
            by.append(
                _("by category %(category)s") % {"category": self.data["category"].name}
            )
        if self.data.get("status"):
            by.append(
                _("by status %(status)s")
                % {"status": FOIREQUEST_FILTER_DICT[self.data["status"]][1]}
            )
        if self.data.get("tag"):
            by.append(_("by tag %(tag)s") % {"tag": self.data["tag"].name})
        if self.data.get("jurisdiction"):
            by.append(_("for %(juris)s") % {"juris": self.data["jurisdiction"].name})
        if self.data.get("publicbody"):
            by.append(
                _("to %(publicbody)s") % {"publicbody": self.data["publicbody"].name}
            )
        return " ".join(str(x) for x in by)

    @clean_feed_output
    def title(self, obj):
        by = self.get_filter_string()
        if by:
            return _("Freedom of Information Requests %(by)s on %(sitename)s") % {
                "sitename": settings.SITE_NAME,
                "by": by,
            }
        return _("Freedom of Information Requests on %(sitename)s") % {
            "sitename": settings.SITE_NAME
        }

    @clean_feed_output
    def description(self, obj):
        by = self.get_filter_string()
        if by:
            return _(
                "This feed contains the Freedom of Information requests %(by)s"
                " that have been made through %(sitename)s."
            ) % {"sitename": settings.SITE_NAME, "by": by}
        return _(
            "This feed contains the latest Freedom of Information requests"
            " that have been made through %(sitename)s."
        ) % {"sitename": settings.SITE_NAME}

    def link(self):
        return self.make_url(self.url_name)

    def items(self):
        return self.items.order_by("-created_at")[:15]

    @clean_feed_output
    def item_title(self, item):
        if item.public_body:
            pb_name = item.public_body.name
        else:
            pb_name = _("Not yet known")
        return _("'%(title)s' to %(publicbody)s") % {
            "title": item.title,
            "publicbody": pb_name,
        }

    @clean_feed_output
    def item_description(self, item):
        return linebreaksbr(item.get_description())

    def item_pubdate(self, item):
        return item.created_at


class LatestFoiRequestsFeedAtom(LatestFoiRequestsFeed):
    feed_type = Atom1Feed
    subtitle = LatestFoiRequestsFeed.description
    url_name = "foirequest-list_feed_atom"


class FoiRequestFeed(Feed):
    def get_object(self, request, slug):
        return get_object_or_404(
            FoiRequest,
            slug=slug,
            public=True,
            visibility=FoiRequest.VISIBILITY.VISIBLE_TO_PUBLIC,
        )

    @clean_feed_output
    def title(self, obj):
        return obj.title

    def link(self, obj):
        return reverse("foirequest-feed", kwargs={"slug": obj.slug})

    @clean_feed_output
    def description(self, obj):
        return obj.get_description()

    def items(self, obj):
        return obj.foievent_set.filter(event_name__in=EVENT_DETAILS).order_by(
            "-timestamp"
        )[:15]

    @clean_feed_output
    def item_title(self, item):
        return item.as_text()

    @clean_feed_output
    def item_description(self, item):
        return linebreaksbr(item.as_text())

    def item_pubdate(self, item):
        return item.timestamp


class FoiRequestFeedAtom(FoiRequestFeed):
    feed_type = Atom1Feed
    subtitle = FoiRequestFeed.description

    def link(self, obj):
        return reverse("foirequest-feed_atom", kwargs={"slug": obj.slug})
