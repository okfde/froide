from django.contrib import admin
from froide.publicbody.models import (PublicBody, FoiLaw, PublicBodyTopic,
        Jurisdiction)


class PublicBodyAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('name', 'email', 'url', 'classification', 'topic', 'depth',)
    list_filter = ('classification', 'topic', 'jurisdiction',)
    search_fields = ['name', "description"]
    exclude = ('confirmed',)


class FoiLawAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("jurisdiction", "name",)}
    list_display = ('name', 'meta', 'jurisdiction',)


class JurisdictionAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}


class PublicBodyTopicAdmin(admin.ModelAdmin):
    pass

admin.site.register(PublicBody, PublicBodyAdmin)
admin.site.register(FoiLaw, FoiLawAdmin)
admin.site.register(Jurisdiction, JurisdictionAdmin)
admin.site.register(PublicBodyTopic, PublicBodyTopicAdmin)
