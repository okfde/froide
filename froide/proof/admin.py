from django.contrib import admin

from froide.account.auth import MFAAndRecentAuthRequiredAdminMixin
from froide.account.models import annotate_deterministic_field
from froide.helper.admin_utils import ForeignKeyFilter

from .models import Proof


@admin.register(Proof)
class ProofAdmin(MFAAndRecentAuthRequiredAdminMixin, admin.ModelAdmin):
    raw_id_fields = ("user",)
    list_display = ("user", "name", "timestamp")
    list_filter = (("user", ForeignKeyFilter),)
    exclude = ("key", "file")
    search_fields = ("user_email_deterministic",)

    def has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = (
            super()
            .get_queryset(request)
            .annotate(
                user_email_deterministic=annotate_deterministic_field("user__email")
            )
        )
        return qs
