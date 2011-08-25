from django.conf.urls.defaults import patterns, url
from django.utils.translation import pgettext

urlpatterns = patterns("",
    url(r"^(?P<slug>[-\w]+)/follow/$", 'foirequestfollower.views.follow', name="foirequestfollower-follow"),

    (r'^%s/(?P<follow_id>\d+)/(?P<check>[0-9a-f]{32})/$' %
        pgettext('URL part', 'confirm-follow'), 'foirequestfollower.views.confirm_follow',
        {}, 'foirequestfollower-confirm_follow'),
    (r'^%s/(?P<follow_id>\d+)/(?P<check>[0-9a-f]{32})/$' %
        pgettext('URL part', 'confirm-unfollow'), 'foirequestfollower.views.confirm_unfollow',
        {}, 'foirequestfollower-confirm_unfollow'),
)
