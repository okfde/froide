from django.conf.urls import url

from ..views import (
    MyRequestsView, DraftRequestsView, FoiProjectListView,
    FollowingRequestsView
)

urlpatterns = [
    url(r'^requests/$', MyRequestsView.as_view(), name='account-requests'),
    url(r'^drafts/$', DraftRequestsView.as_view(), name='account-drafts'),
    url(r'^projects/$', FoiProjectListView.as_view(), name='account-projects'),
    url(r'^following/$', FollowingRequestsView.as_view(), name='account-following'),
]
