from django.conf.urls import url

from .views import reset_token


urlpatterns = [
    url(r'^reset/$', reset_token, name='accesstoken-reset'),
]
