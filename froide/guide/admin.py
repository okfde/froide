from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from froide.helper.admin_utils import ForeignKeyFilter, make_nullfilter

from .models import Action, Guidance, Rule
from .utils import notify_guidance


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ("name", "priority", "is_active")
    list_filter = ("priority", "is_active")
    search_fields = ("name",)

    raw_id_fields = ("publicbodies", "categories")


@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = ("name", "label", "mail_intent", "tag", "letter_template")
    search_fields = (
        "name",
        "label",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related("tag", "letter_template")
        return qs


@admin.register(Guidance)
class GuidanceAdmin(admin.ModelAdmin):
    raw_id_fields = (
        "message",
        "user",
    )
    date_hierarchy = "timestamp"
    list_display = ("message", "action", "timestamp")
    list_filter = (
        "action",
        ("message", ForeignKeyFilter),
        make_nullfilter("rule", _("Has rule")),
    )
    actions = ["send_notification"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.prefetch_related("message", "action")
        return qs

    @admin.action(description=_("Send notification about selected guidance items"))
    def send_notification(self, request, queryset):
        for guidance in queryset:
            notify_guidance(guidance)
