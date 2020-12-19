from django.urls import re_path

from .views import profile

urlpatterns = [
    re_path(r'^(?P<slug>[-\w\.]+)/$', profile, name='account-profile')
]
