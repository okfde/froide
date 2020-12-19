from django.urls import path

from .views import report_problem


urlpatterns = [
    path('report/message/<int:message_pk>/',
         report_problem, name='problem-report'),
]
