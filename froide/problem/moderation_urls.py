from django.conf.urls import url

from .views import moderation_view


urlpatterns = [
    url(r'^$', moderation_view, name='problem-moderation'),
]
