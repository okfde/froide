from django.conf.urls.defaults import patterns, url

from foirequest.feeds import FoiRequestFeed, FoiRequestFeedAtom


urlpatterns = patterns("",
    url(r"^(?P<slug>[-\w]+)/$", 'foirequest.views.show', name="foirequest-show"),
    url(r"^(?P<slug>[-\w]+)/feed/$", FoiRequestFeedAtom(), name="foirequest-feed_atom"),
    url(r"^(?P<slug>[-\w]+)/rss/$", FoiRequestFeed(), name="foirequest-feed"),
    url(r"^(?P<slug>[-\w]+)/suggest/public-body/$", 'foirequest.views.suggest_public_body', name="foirequest-suggest_public_body"),
    url(r"^(?P<slug>[-\w]+)/set/public-body/$", 'foirequest.views.set_public_body', name="foirequest-set_public_body"),
    url(r"^(?P<slug>[-\w]+)/set/status/$", 'foirequest.views.set_status', name="foirequest-set_status"),
    url(r"^(?P<slug>[-\w]+)/send/message/$", 'foirequest.views.send_message', name="foirequest-send_message"),
    url(r"^(?P<slug>[-\w]+)/make/public/$", 'foirequest.views.make_public', name="foirequest-make_public"),
    url(r"^(?P<slug>[-\w]+)/set/law/$", 'foirequest.views.set_law', name="foirequest-set_law"),
    url(r"^(?P<slug>[-\w]+)/set/resolution/$", 'foirequest.views.set_resolution', name="foirequest-set_resolution"),

    url(r"^(?P<slug>[-\w]+)/add/postal-reply/$", 'foirequest.views.add_postal_reply', name="foirequest-add_postal_reply"),
    url(r"^(?P<slug>[-\w]+)/add/postal-reply/(?P<message_id>\d+)/$", 'foirequest.views.add_postal_reply_attachment', name="foirequest-add_postal_reply_attachment"),
    url(r"^(?P<slug>[-\w]+)/(?P<message_id>\d+)/set/public-body/$", 'foirequest.views.set_message_sender', name="foirequest-set_message_sender"),
    url(r"^(?P<slug>[-\w]+)/mark/not-foi/$", 'foirequest.views.mark_not_foi', name="foirequest-mark_not_foi"),
    url(r"^(?P<slug>[-\w]+)/mark/checked/$", 'foirequest.views.mark_checked', name="foirequest-mark_checked"),


)
