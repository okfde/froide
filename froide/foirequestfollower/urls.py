from django.urls import path, re_path
from django.utils.translation import pgettext_lazy

from .views import follow, confirm_follow, unfollow_by_link

urlpatterns = [
    path("<int:pk>/follow/", follow, name="foirequestfollower-follow"),

    re_path(pgettext_lazy('url part', r'^confirm/(?P<follow_id>\d+)/(?P<check>[0-9a-f]{32})/$'),
        confirm_follow, name='foirequestfollower-confirm_follow'),
    re_path(pgettext_lazy('url part', r'^unfollow/(?P<follow_id>\d+)/(?P<check>[0-9a-f]{32})/$'),
        unfollow_by_link,
        name='foirequestfollower-confirm_unfollow'),
]
