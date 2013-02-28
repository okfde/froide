from django.conf.urls import patterns, url
from django.utils.translation import pgettext

urlpatterns = patterns("froide.foirequestfollower.views",
    url(r"^(?P<slug>[-\w]+)/follow/$", 'follow', name="foirequestfollower-follow"),

    (r'^%s/(?P<follow_id>\d+)/(?P<check>[0-9a-f]{32})/$' %
        pgettext('URL part', 'confirm-follow'), 'confirm_follow',
        {}, 'foirequestfollower-confirm_follow'),
    (r'^%s/(?P<follow_id>\d+)/(?P<check>[0-9a-f]{32})/$' %
        pgettext('URL part', 'unfollow'), 'unfollow_by_link',
        {}, 'foirequestfollower-confirm_unfollow'),
)
