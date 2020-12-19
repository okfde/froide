from django.urls import path

from .views import rerun_rules


urlpatterns = [
    path('guide/rerun/<int:message_id>/', rerun_rules,
         name='guide-rerun_rules'),
]
