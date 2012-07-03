from django.conf import settings
from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404

from .models import FoiRequest


class LatestFoiRequestsFeed(Feed):
    title = _("Latest Freedom of Information Requests on %(sitename)s") % {"sitename": settings.SITE_NAME}
    description = _("This feed contains the latest Freedom of Information requests that have been made through %(sitename)s.") % {"sitename": settings.SITE_NAME}

    def link(self):
        return reverse('foirequest-feed_latest')

    def items(self):
        return FoiRequest.published.get_for_latest_feed()

    def item_title(self, item):
        if item.public_body:
            pb_name = item.public_body.name
        else:
            pb_name = _("Not yet known")
        return _("'%(title)s' to %(publicbody)s") % {
            "title": item.title,
            "publicbody": pb_name
        }

    def item_description(self, item):
        return item.description

    def item_pubdate(self, item):
        return item.first_message


class LatestFoiRequestsFeedAtom(LatestFoiRequestsFeed):
    feed_type = Atom1Feed
    subtitle = LatestFoiRequestsFeed.description

    def link(self):
        return reverse('foirequest-feed_latest_atom')


class FoiRequestFeed(Feed):
    def get_object(self, request, slug):
        return get_object_or_404(FoiRequest, slug=slug, public=True)

    def title(self, obj):
        return obj.title

    def link(self, obj):
        return reverse('foirequest-feed', kwargs={"slug": obj.slug})

    def description(self, obj):
        return obj.description

    def items(self, obj):
        return obj.foievent_set.order_by("-timestamp")[:15]

    def item_title(self, item):
        return item.as_text()

    def item_description(self, item):
        return item.as_text()

    def item_pubdate(self, item):
        return item.timestamp


class FoiRequestFeedAtom(FoiRequestFeed):
    feed_type = Atom1Feed
    subtitle = FoiRequestFeed.description

    def link(self, obj):
        return reverse('foirequest-feed_atom', kwargs={"slug": obj.slug})
