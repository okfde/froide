from django.contrib import admin

from foirequestfollower.models import FoiRequestFollower

class FoiRequestFollowerAdmin(admin.ModelAdmin):
    pass


admin.site.register(FoiRequestFollower, FoiRequestFollowerAdmin)
