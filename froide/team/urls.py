from django.urls import path

from .views import (
    ChangeTeamMemberRoleView,
    CreateTeamView,
    DeleteTeamMemberRoleView,
    DeleteTeamView,
    InviteTeamMemberView,
    JoinTeamUserView,
    JoinTeamView,
    TeamDetailView,
    TeamListView,
)

urlpatterns = [
    path("", TeamListView.as_view(), name="team-list"),
    path("create/", CreateTeamView.as_view(), name="team-create"),
    path("<int:pk>/", TeamDetailView.as_view(), name="team-detail"),
    path("<int:pk>/invite/", InviteTeamMemberView.as_view(), name="team-invite"),
    path("<int:pk>/delete/", DeleteTeamView.as_view(), name="team-delete"),
    path(
        "<int:pk>/change-member/",
        ChangeTeamMemberRoleView.as_view(),
        name="team-change_member",
    ),
    path(
        "<int:pk>/delete-member/",
        DeleteTeamMemberRoleView.as_view(),
        name="team-delete_member",
    ),
    path("join/<int:pk>/", JoinTeamUserView.as_view(), name="team-join_user"),
    path("join/<int:pk>/<str:secret>/", JoinTeamView.as_view(), name="team-join"),
]
