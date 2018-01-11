from django.contrib import admin

from .models import Team, TeamMembership


class TeamMembershipInline(admin.StackedInline):
    model = TeamMembership
    raw_id_fields = ('user', 'team',)


class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'created', 'member_count')
    inlines = [TeamMembershipInline]


admin.site.register(Team, TeamAdmin)
