from django.conf.urls import patterns, url

from .feeds import FoiRequestFeed, FoiRequestFeedAtom


urlpatterns = patterns("froide.foirequest.views",
    url(r"^(?P<obj_id>\d+)$", 'shortlink', name="foirequest-notsolonglink"),
    url(r"^(?P<obj_id>\d+)/auth/(?P<code>[0-9a-f]+)/$", 'auth', name="foirequest-longerauth"),
    url(r"^(?P<slug>[-\w]+)/$", 'show', name="foirequest-show"),
    url(r"^(?P<slug>[-\w]+)/suggest/public-body/$", 'suggest_public_body', name="foirequest-suggest_public_body"),
    url(r"^(?P<slug>[-\w]+)/set/public-body/$", 'set_public_body', name="foirequest-set_public_body"),
    url(r"^(?P<slug>[-\w]+)/set/status/$", 'set_status', name="foirequest-set_status"),
    url(r"^(?P<slug>[-\w]+)/send/message/$", 'send_message', name="foirequest-send_message"),
    url(r"^(?P<slug>[-\w]+)/escalation/message/$", 'escalation_message', name="foirequest-escalation_message"),
    url(r"^(?P<slug>[-\w]+)/make/public/$", 'make_public', name="foirequest-make_public"),
    url(r"^(?P<slug>[-\w]+)/set/law/$", 'set_law', name="foirequest-set_law"),
    url(r"^(?P<slug>[-\w]+)/set/tags/$", 'set_tags', name="foirequest-set_tags"),
    url(r"^(?P<slug>[-\w]+)/set/resolution/$", 'set_summary', name="foirequest-set_summary"),
    url(r"^(?P<slug>[-\w]+)/add/postal-reply/$", 'add_postal_reply', name="foirequest-add_postal_reply"),
    url(r"^(?P<slug>[-\w]+)/add/postal-reply/(?P<message_id>\d+)/$", 'add_postal_reply_attachment', name="foirequest-add_postal_reply_attachment"),
    url(r"^(?P<slug>[-\w]+)/(?P<message_id>\d+)/set/public-body/$", 'set_message_sender', name="foirequest-set_message_sender"),
    url(r"^(?P<slug>[-\w]+)/mark/not-foi/$", 'mark_not_foi', name="foirequest-mark_not_foi"),
    url(r"^(?P<slug>[-\w]+)/mark/checked/$", 'mark_checked', name="foirequest-mark_checked"),
    url(r"^(?P<slug>[-\w]+)/extend-deadline/$", 'extend_deadline', name="foirequest-extend_deadline"),
    url(r"^(?P<slug>[-\w]+)/approve/(?P<attachment>\d+)/$", 'approve_attachment', name="foirequest-approve_attachment"),
    url(r"^(?P<slug>[-\w]+)/approve/message/(?P<message>\d+)/$", 'approve_message', name="foirequest-approve_message"),
    url(r"^(?P<slug>[-\w]+)/make-same/(?P<message_id>\d+)/$", 'make_same_request', name="foirequest-make_same_request"),
    url(r"^(?P<slug>[-\w]+)/resend/$", 'resend_message', name="foirequest-resend_message"),
    # Redaction
    url(r"^(?P<slug>[-\w]+)/redact/(?P<attachment_id>\d+)/$", 'redact_attachment', name="foirequest-redact_attachment"),
)

# Feed
urlpatterns += patterns("",
    url(r"^(?P<slug>[-\w]+)/feed/$", FoiRequestFeedAtom(), name="foirequest-feed_atom"),
    url(r"^(?P<slug>[-\w]+)/rss/$", FoiRequestFeed(), name="foirequest-feed")
)
