from django.urls import path
from django.utils.translation import pgettext_lazy

from .views import confirm_follow, embed_follow, follow, unfollow_by_link

app_name = "follow"
urlpatterns = [
    path("<str:conf_slug>-<int:pk>/follow/", follow, name="follow"),
    path("<int:pk>/follow/", follow, name="follow"),
    path(
        "<str:conf_slug>-<int:pk>/follow/embed/",
        embed_follow,
        name="follow_embed",
    ),
    path("<int:pk>/follow/embed/", embed_follow, name="follow_embed"),
    path(
        pgettext_lazy(
            "url part", "confirm/<str:conf_slug>-<int:follow_id>/<str:check>/"
        ),
        confirm_follow,
        name="confirm_follow",
    ),
    path(
        pgettext_lazy("url part", "confirm/<int:follow_id>/<str:check>/"),
        confirm_follow,
        name="confirm_follow",
    ),
    path(
        pgettext_lazy(
            "url part", "unfollow/<str:conf_slug>-<int:follow_id>/<str:check>/"
        ),
        unfollow_by_link,
        name="confirm_unfollow",
    ),
    path(
        pgettext_lazy("url part", "unfollow/<int:follow_id>/<str:check>/"),
        unfollow_by_link,
        name="confirm_unfollow",
    ),
]
