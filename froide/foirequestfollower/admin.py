from django.contrib import admin

from froide.follow.admin import FollowerAdmin

from .models import FoiRequestFollower

admin.site.register(FoiRequestFollower, FollowerAdmin)
