from django.urls import path

from ..views import ProjectView, SetProjectTeamView

urlpatterns = [
    path("<slug:slug>/", ProjectView.as_view(), name="foirequest-project"),
    path("<slug:slug>/set-team/", SetProjectTeamView.as_view(),
         name="foirequest-project_set_team")
]
