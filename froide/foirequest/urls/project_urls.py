from django.conf.urls import url

from ..views import ProjectView

urlpatterns = [
    url(r"^(?P<slug>[-\w]+)/$", ProjectView.as_view(), name="foirequest-project")
]
