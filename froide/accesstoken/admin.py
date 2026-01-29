from django.contrib import admin

from froide.account.auth import MFAAndRecentAuthRequiredAdminMixin
from froide.account.models import annotate_deterministic_field

from .models import AccessToken


@admin.register(AccessToken)
class AccessTokenAdmin(MFAAndRecentAuthRequiredAdminMixin, admin.ModelAdmin):
    raw_id_fields = ("user",)
    list_filter = ("purpose",)
    search_fields = ("user_email_deterministic",)

    def get_queryset(self, request):
        qs = (
            super()
            .get_queryset(request)
            .annotate(
                user_email_deterministic=annotate_deterministic_field("user__email")
            )
        )
        return qs
