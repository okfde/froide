from django.contrib import admin
from froide.account.models import Profile


class ProfileAdmin(admin.ModelAdmin):
    pass

admin.site.register(Profile, ProfileAdmin)
