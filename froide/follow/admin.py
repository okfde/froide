from django.contrib import admin

from froide.helper.admin_utils import ForeignKeyFilter


class FollowerAdmin(admin.ModelAdmin):
    raw_id_fields = (
        "user",
        "content_object",
    )
    date_hierarchy = "timestamp"
    list_display = ("user", "email", "content_object", "timestamp", "confirmed")
    list_filter = (
        "confirmed",
        ("content_object", ForeignKeyFilter),
        ("user", ForeignKeyFilter),
    )
    search_fields = ("email",)
    actions = []

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("user", "content_object")
