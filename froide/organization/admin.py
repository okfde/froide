from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Organization, OrganizationMembership


class OrganizationMembershipInline(admin.StackedInline):
    model = OrganizationMembership
    raw_id_fields = ("user",)


class OrganizationAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "website", "member_count", "show_in_list")
    inlines = [OrganizationMembershipInline]
    actions = ["show_in_list"]
    list_filter = ["show_in_list"]

    @admin.action(description=_("Show selected organizations in public list"))
    def show_in_list(self, request, queryset):
        queryset.update(show_in_list=True)


admin.site.register(Organization, OrganizationAdmin)
