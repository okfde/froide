from django.urls import path

from .views import profile

urlpatterns = [
    path('<str:slug>/', profile, name='account-profile')
]
