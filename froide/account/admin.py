from django.contrib import admin
from froide.account.models import Profile


class ProfileAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'user__email']
    list_display = ('user', 'address')

admin.site.register(Profile, ProfileAdmin)
