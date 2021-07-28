from django.conf import settings
from django.contrib.syndication.views import Feed
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from froide.helper.search.facets import make_filter_url
from froide.helper.feed_utils import clean_feed_output


class DocumentSearchFeed(Feed):
    url_name = 'document-search_feed'

    def __init__(self, items, data):
        self.items = items
        self.data = data
        super().__init__()

    def get_filter_string(self):
        by = []
        if self.data.get('q'):
            by.append(_('matching the query “%s”' % self.data['q']))
        if self.data.get('tag'):
            by.append(_('by tag %(tag)s') % {'tag': self.data['tag'].name})
        if self.data.get('jurisdiction'):
            by.append(_('from %(juris)s') % {'juris': self.data['jurisdiction'].name})
        if self.data.get('publicbody'):
            by.append(_('from %(publicbody)s') % {'publicbody': self.data['publicbody'].name})
        if self.data.get('campaign'):
            by.append(_('resulting from campaign “%(campaign)s”') % {'campaign': self.data['campaign'].name})
        return ' '.join(str(x) for x in by)

    @clean_feed_output
    def title(self, obj):
        by = self.get_filter_string()
        if by:
            return _("Documents %(by)s on %(sitename)s") % {
                "sitename": settings.SITE_NAME,
                'by': by
            }

        return _("Documents on %(sitename)s") % {
            "sitename": settings.SITE_NAME
        }

    @clean_feed_output
    def description(self, obj):
        by = self.get_filter_string()
        if by:
            return _("This feed contains documents %(by)s"
                " on %(sitename)s.") % {
                    "sitename": settings.SITE_NAME,
                    'by': by
                }
        return _("This feed contains the latest documents"
            " that appear on %(sitename)s.") % {
                "sitename": settings.SITE_NAME
            }

    def link(self):
        return make_filter_url(self.url_name, self.data)

    def items(self):
        return self.items[:15]

    @clean_feed_output
    def item_title(self, item):
        return _('{title} (page {page})').format(
            title=item.document.title, page=item.number
        )

    @clean_feed_output
    def item_description(self, item):
        return format_html(
            '<p>{description}</p><p>%s</p>' % item.query_highlight,
            description=item.document.description,
        )

    def item_pubdate(self, item):
        return item.document.published_at or item.document.created_at
