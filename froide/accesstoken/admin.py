from django.contrib import admin

from .models import AccessToken


class AccessTokenAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_filter = ('purpose',)
    search_fields = ('user__email',)


admin.site.register(AccessToken, AccessTokenAdmin)
