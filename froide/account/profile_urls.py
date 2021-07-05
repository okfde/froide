from django.urls import path

from .views import ProfileView

urlpatterns = [
    path('<str:slug>/', ProfileView.as_view(), name='account-profile')
]
