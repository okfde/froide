from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from froide.account.models import User


class UserAdmin(DjangoUserAdmin):
    fieldsets = list(DjangoUserAdmin.fieldsets) + [
        (_('Profile info'), {'fields': ('address', 'organization',
            'organization_url', 'private', 'terms', 'newsletter')})
    ]
    list_filter = list(DjangoUserAdmin.list_filter) + ['terms', 'newsletter']


admin.site.register(User, UserAdmin)
