from django.contrib import admin

from froide.account.auth import MFAAndRecentAuthRequiredAdminMixin
from froide.helper.admin_utils import ForeignKeyFilter

from .models import Proof


@admin.register(Proof)
class ProofAdmin(MFAAndRecentAuthRequiredAdminMixin, admin.ModelAdmin):
    raw_id_fields = ("user",)
    list_display = ("user", "name", "timestamp")
    list_filter = (("user", ForeignKeyFilter),)
    exclude = ("key", "file")
    search_fields = ("user__email_deterministic",)

    def has_change_permission(self, request, obj=None):
        return False
