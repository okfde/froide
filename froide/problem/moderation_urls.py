from django.urls import path

from .views import moderate_user, moderation_view

urlpatterns = [
    path("", moderation_view, name="problem-moderation"),
    path("user/<int:pk>/", moderate_user, name="problem-user"),
]
