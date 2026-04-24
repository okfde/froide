from django.urls import path
from django.utils.translation import pgettext_lazy

from .views import (
    change_alert,
    confirm_alert,
    list_alerts,
    subscribe_alert,
    unsubscribe,
)

app_name = "searchalert"
urlpatterns = [
    path("", list_alerts, name="list"),
    path("subscribe-alert/", subscribe_alert, name="subscribe"),
    path(
        pgettext_lazy("url part", "confirm/<int:alert_id>/<str:check>/"),
        confirm_alert,
        name="confirm_subscribe",
    ),
    path(
        pgettext_lazy("url part", "change/<int:alert_id>/"),
        change_alert,
        name="change",
    ),
    path(
        pgettext_lazy("url part", "change/<int:alert_id>/<str:check>/"),
        change_alert,
        name="change",
    ),
    path(
        pgettext_lazy("url part", "unsubscribe/<int:alert_id>/"),
        unsubscribe,
        name="unsubscribe",
    ),
    path(
        pgettext_lazy("url part", "unsubscribe/<int:alert_id>/<str:check>/"),
        unsubscribe,
        name="unsubscribe",
    ),
]
