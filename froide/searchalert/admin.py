from django.contrib import admin

from froide.helper.admin_utils import ForeignKeyFilter

from .models import Alert


class AlertAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)
    date_hierarchy = "created_at"
    list_display = ("query", "created_at", "user", "email", "email_confirmed")
    list_filter = (
        "email_confirmed",
        ("user", ForeignKeyFilter),
    )
    search_fields = ("email",)
    actions = ["trigger_confirmation_mail", "send_preview_update"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("user")

    def trigger_confirmation_mail(self, request, queryset):
        for alert in queryset.exclude(email="").filter(email_confirmed__isnull=True):
            alert.send_confirm_alert_mail()

    def send_update(self, request, queryset):
        from .tasks import update_alert_subscription

        for alert in queryset:
            update_alert_subscription.delay(alert.id, force=True)

    def send_preview_update(self, request, queryset):
        from .tasks import update_alert_subscription

        for alert in queryset:
            update_alert_subscription.delay(alert.id, preview=True)


admin.site.register(Alert, AlertAdmin)
