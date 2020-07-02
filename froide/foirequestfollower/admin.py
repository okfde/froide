from django.contrib import admin

from froide.helper.admin_utils import ForeignKeyFilter

from .models import FoiRequestFollower


class FoiRequestFollowerAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', 'request',)
    date_hierarchy = 'timestamp'
    list_display = ('user', 'email', 'request', 'timestamp', 'confirmed')
    list_filter = (
        'confirmed',
        ('request', ForeignKeyFilter),
        ('user', ForeignKeyFilter),
    )
    search_fields = ('email',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('user', 'request')


admin.site.register(FoiRequestFollower, FoiRequestFollowerAdmin)
