from django.urls import path

from .views import reset_token

urlpatterns = [
    path("reset/", reset_token, name="accesstoken-reset"),
]
