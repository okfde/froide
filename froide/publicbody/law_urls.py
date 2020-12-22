from django.urls import path

from .views import show_foilaw

urlpatterns = [
    path("<slug:slug>/", show_foilaw, name="publicbody-foilaw-show"),
]
