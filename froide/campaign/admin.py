from django.contrib import admin

from .models import Campaign


class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'public',
    )
    date_hierarchy = 'start_date'
    ordering = ('-start_date',)
    prepopulated_fields = {
        'slug': ('name',)
    }


admin.site.register(Campaign, CampaignAdmin)
