from django.urls import path
from django.utils.translation import pgettext_lazy

from .views import follow, confirm_follow, unfollow_by_link

urlpatterns = [
    path("<int:pk>/follow/", follow, name="foirequestfollower-follow"),

    path(pgettext_lazy('url part', 'confirm/<int:follow_id>/<str:check>/'),
        confirm_follow, name='foirequestfollower-confirm_follow'),
    path(pgettext_lazy('url part', 'unfollow/<int:follow_id>/<str:check>/'),
        unfollow_by_link,
        name='foirequestfollower-confirm_unfollow'),
]
