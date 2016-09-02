from django.conf.urls import url

from .views import show_foilaw

urlpatterns = [
    url(r"^(?P<slug>[-\w]+)/$", show_foilaw, name="publicbody-foilaw-show"),
]
