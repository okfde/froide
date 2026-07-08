from django.urls import re_path

from .views import unsubscribe_view

app_name = "bounce"
urlpatterns = [
    re_path(r"^(?P<reference>[^/]+)/$", unsubscribe_view, name="unsubscribe"),
]
