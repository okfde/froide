from django.conf.urls import url

from .views import rerun_rules


urlpatterns = [
    url(r'^guide/rerun/(?P<message_id>\d+)/$', rerun_rules, name='guide-rerun_rules'),
]
