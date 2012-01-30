from django.contrib import admin
from froide.frontpage.models import FeaturedRequest


class FeaturedRequestAdmin(admin.ModelAdmin):
    list_display = ('request', 'title', 'user', 'timestamp',)
    search_fields = ['title', 'request__title']
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    raw_id_fields = ('request', 'user',)

admin.site.register(FeaturedRequest, FeaturedRequestAdmin)
