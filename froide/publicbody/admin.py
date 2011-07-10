from django.contrib import admin
from froide.publicbody.models import PublicBody, FoiLaw, PublicBodyTopic

class PublicBodyAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("geography", "name",)}
    list_display = ('name', 'email', 'url', 'classification', 'topic', 'depth',)
    list_filter = ('classification', 'topic',)
    search_fields = ['name', "description"]
    exclude = ('confirmed',)

class FoiLawAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("jurisdiction", "name",)}
    list_display = ('name', 'meta',)


class PublicBodyTopicAdmin(admin.ModelAdmin):
    pass

admin.site.register(PublicBody, PublicBodyAdmin)
admin.site.register(FoiLaw, FoiLawAdmin)
admin.site.register(PublicBodyTopic, PublicBodyTopicAdmin)
