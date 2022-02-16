from django.contrib import admin

from .models import Organization, OrganizationMembership


class OrganizationMembershipInline(admin.StackedInline):
    model = OrganizationMembership
    raw_id_fields = ("user",)


class OrganizationAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "website", "created", "member_count")
    inlines = [OrganizationMembershipInline]


admin.site.register(Organization, OrganizationAdmin)
