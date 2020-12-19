from django.urls import path

from .views import moderation_view


urlpatterns = [
    path('', moderation_view, name='problem-moderation'),
]
