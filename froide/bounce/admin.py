from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from .models import Bounce


class BounceAdmin(admin.ModelAdmin):
    list_display = ('email', 'user', 'user_is_active', 'last_update')
    list_filter = ('user__is_active', 'user__is_deleted')
    raw_id_fields = ('user',)
    actions = ['deactivate_users']

    def user_is_active(self, obj):
        if obj.user:
            return obj.user.is_active
        return None
    user_is_active.boolean = True

    def deactivate_users(self, request, queryset):
        queryset = queryset.filter(
            user__isnull=False, user__is_active=True
            ).select_related('user')

        for bounce in queryset:
            bounce.user.deactivate()
    deactivate_users.short_description = _('Deactivate bounced accounts')


admin.site.register(Bounce, BounceAdmin)
