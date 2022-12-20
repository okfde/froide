from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from froide.helper.admin_utils import make_nullfilter

from .models import ProblemReport


@admin.register(ProblemReport)
class ProblemReportAdmin(admin.ModelAdmin):
    date_hierarchy = "timestamp"
    raw_id_fields = ("message", "user", "moderator")
    list_filter = (
        "auto_submitted",
        "resolved",
        "kind",
        make_nullfilter("claimed", _("Claimed")),
        make_nullfilter("escalated", _("Escalated")),
    )
    list_display = (
        "kind",
        "timestamp",
        "admin_link_message",
        "auto_submitted",
        "moderator",
        "resolved",
    )
    actions = ["resolve_all"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related("message", "moderator")
        return qs

    def admin_link_message(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse("admin:foirequest_foimessage_change", args=(obj.message_id,)),
            str(obj.message.subject),
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if "resolved" in form.changed_data and obj.resolved:
            sent = obj.resolve(request.user, resolution=obj.resolution)
            if sent:
                self.message_user(request, _("User will be notified of resolution"))

    @admin.action(description=_("Resolve selected"))
    def resolve_all(self, request, queryset):
        count = 0
        for problem in queryset.filter(resolved=False):
            sent = problem.resolve(request.user, resolution="")
            if sent:
                count += 1

        self.message_user(
            request,
            _("Problems marked as resolved, {count} users will be notified.").format(
                count=count
            ),
        )
