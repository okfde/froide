from django.urls import path
from django.utils.translation import pgettext_lazy

from .views import (
    ChangeOrganizationMemberRoleView,
    DeleteOrganizationMemberView,
    InviteOrganizationMemberView,
    JoinOrganizationView,
    OrganizationDetailView,
    OrganizationListView,
    OrganizationUpdateView,
)

urlpatterns = [
    path(
        "",
        OrganizationListView.as_view(),
        name="organization-list",
    ),
    path(
        pgettext_lazy("url part", "<str:slug>/"),
        OrganizationDetailView.as_view(),
        name="organization-detail",
    ),
    path(
        pgettext_lazy("url part", "<str:slug>/update/"),
        OrganizationUpdateView.as_view(),
        name="organization-update",
    ),
    path(
        pgettext_lazy("url part", "organization/<str:slug>/invite/"),
        InviteOrganizationMemberView.as_view(),
        name="organization-invite",
    ),
    path(
        pgettext_lazy("url part", "<str:slug>/delete-member/<int:pk>/"),
        DeleteOrganizationMemberView.as_view(),
        name="organization-delete_member",
    ),
    path(
        pgettext_lazy("url part", "<str:slug>/change-member/<int:pk>/"),
        ChangeOrganizationMemberRoleView.as_view(),
        name="organization-change_member",
    ),
    path(
        pgettext_lazy("url part", "<str:slug>/join/<int:pk>/<str:secret>/"),
        JoinOrganizationView.as_view(),
        name="organization-join",
    ),
]
