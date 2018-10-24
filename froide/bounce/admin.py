from django.contrib import admin

from .models import Bounce


class BounceAdmin(admin.ModelAdmin):
    list_display = ('email', 'user', 'last_update')
    raw_id_fields = ('user',)


admin.site.register(Bounce, BounceAdmin)
