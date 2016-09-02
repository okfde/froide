from django.conf.urls import url
from django.utils.translation import pgettext

from .views import follow, confirm_follow, unfollow_by_link

urlpatterns = [
    url(r"^(?P<slug>[-\w]+)/follow/$", follow, name="foirequestfollower-follow"),

    url(r'^%s/(?P<follow_id>\d+)/(?P<check>[0-9a-f]{32})/$' %
        pgettext('URL part', 'confirm-follow'), confirm_follow,
        name='foirequestfollower-confirm_follow'),
    url(r'^%s/(?P<follow_id>\d+)/(?P<check>[0-9a-f]{32})/$' %
        pgettext('URL part', 'unfollow'), unfollow_by_link,
        name='foirequestfollower-confirm_unfollow'),
]
