from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from froide.account.models import User


class UserAdmin(DjangoUserAdmin):
    fieldsets = list(DjangoUserAdmin.fieldsets) + [
        (_('Profile info'), {'fields': ('address', 'organization',
            'organization_url', 'private')})
    ]


admin.site.register(User, UserAdmin)
