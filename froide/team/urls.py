from django.conf.urls import url

from .views import (
    TeamListView, TeamDetailView, CreateTeamView, InviteTeamMemberView,
    JoinTeamView, ChangeTeamMemberRoleView, DeleteTeamMemberRoleView
)

urlpatterns = [
    url(r'^$', TeamListView.as_view(), name='team-list'),
    url(r'^create/$', CreateTeamView.as_view(), name='team-create'),
    url(r'^(?P<pk>\d+)/$', TeamDetailView.as_view(), name='team-detail'),
    url(r'^(?P<pk>\d+)/invite/$', InviteTeamMemberView.as_view(), name='team-invite'),
    url(r'^(?P<pk>\d+)/change-member/$', ChangeTeamMemberRoleView.as_view(), name='team-change_member'),
    url(r'^(?P<pk>\d+)/delete-member/$', DeleteTeamMemberRoleView.as_view(), name='team-delete_member'),
    url(r'^join/(?P<pk>\d+)/(?P<secret>\w+)/$', JoinTeamView.as_view(), name='team-join'),
]
