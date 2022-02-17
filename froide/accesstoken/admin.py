from django.contrib import admin

from froide.account.auth import MFAAndRecentAuthRequiredAdminMixin

from .models import AccessToken


class AccessTokenAdmin(MFAAndRecentAuthRequiredAdminMixin, admin.ModelAdmin):
    raw_id_fields = ("user",)
    list_filter = ("purpose",)
    search_fields = ("user__email",)


admin.site.register(AccessToken, AccessTokenAdmin)
