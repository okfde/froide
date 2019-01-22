from django.contrib import admin

from .models import FoiRequestFollower


class FoiRequestFollowerAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', 'request',)


admin.site.register(FoiRequestFollower, FoiRequestFollowerAdmin)
