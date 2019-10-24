from django.contrib import admin

from .models import FoiRequestFollower


class FoiRequestFollowerAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', 'request',)
    date_hierarchy = 'timestamp'
    list_display = ('user', 'request', 'timestamp', 'confirmed')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('user', 'request')


admin.site.register(FoiRequestFollower, FoiRequestFollowerAdmin)
