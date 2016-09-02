from django.conf.urls import url

from .views import profile

urlpatterns = [
    url(r'^(?P<slug>[-\w\.]+)/$', profile, name='account-profile')
]
