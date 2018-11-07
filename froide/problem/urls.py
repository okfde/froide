from django.conf.urls import url

from .views import report_problem


urlpatterns = [
    url(r'^report/message/(?P<message_pk>\d+)/$', report_problem, name='problem-report'),
]
