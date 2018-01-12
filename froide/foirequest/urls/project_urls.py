from django.conf.urls import url

from ..views import ProjectView, SetProjectTeamView

urlpatterns = [
    url(r"^(?P<slug>[-\w]+)/$", ProjectView.as_view(), name="foirequest-project"),
    url(r"^(?P<slug>[-\w]+)/set-team/$", SetProjectTeamView.as_view(), name="foirequest-project_set_team")
]
