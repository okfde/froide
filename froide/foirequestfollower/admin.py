from django.contrib import admin

from .models import FoiRequestFollower


class FoiRequestFollowerAdmin(admin.ModelAdmin):
    pass


admin.site.register(FoiRequestFollower, FoiRequestFollowerAdmin)
