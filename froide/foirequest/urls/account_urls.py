from django.urls import path

from ..views import (
    MyRequestsView,
    DraftRequestsView,
    FoiProjectListView,
    FollowingRequestsView,
    RequestSubscriptionsView,
)

urlpatterns = [
    path("requests/", MyRequestsView.as_view(), name="account-requests"),
    path("drafts/", DraftRequestsView.as_view(), name="account-drafts"),
    path("projects/", FoiProjectListView.as_view(), name="account-projects"),
    path("following/", FollowingRequestsView.as_view(), name="account-following"),
    path(
        "subscriptions/",
        RequestSubscriptionsView.as_view(),
        name="account-subscriptions",
    ),
]
