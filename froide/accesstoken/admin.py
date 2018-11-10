from django.contrib import admin

from .models import AccessToken


class AccessTokenAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)


admin.site.register(AccessToken, AccessTokenAdmin)
