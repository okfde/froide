from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from django_comments.admin import CommentsAdmin as DjangoCommentsAdmin

from froide.account.models import annotate_deterministic_field
from froide.helper.admin_utils import ForeignKeyFilter

from .models import FroideComment

REMOVED = {"ip_address"}


@admin.register(FroideComment)
class CommentAdmin(DjangoCommentsAdmin):
    fieldsets = (
        (None, {"fields": ("content_type", "object_pk", "site")}),
        (
            _("Content"),
            {"fields": ("user", "user_name", "user_email", "user_url", "comment")},
        ),
        (
            _("Metadata"),
            {"fields": ("submit_date", "is_public", "is_removed", "is_moderation")},
        ),
    )
    list_display = [c for c in DjangoCommentsAdmin.list_display if c not in REMOVED]
    list_filter = [c for c in DjangoCommentsAdmin.list_filter if c not in REMOVED] + [
        ("object_pk", ForeignKeyFilter),
        "is_moderation",
    ]
    search_fields = (
        "comment",
        "user_email_deterministic",
        "user_name",
        "user_email",
        "user_url",
    )
    actions = []

    def get_queryset(self, request):
        qs = (
            super()
            .get_queryset(request)
            .annotate(
                user_email_deterministic=annotate_deterministic_field("user__email")
            )
        )
        return qs
