from django.contrib import admin
from froide.publicbody.models import (PublicBody, FoiLaw, PublicBodyTopic,
        Jurisdiction)


class PublicBodyAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('name', 'email', 'url', 'classification', 'topic', 'jurisdiction',)
    list_filter = ('topic', 'jurisdiction', 'classification')
    search_fields = ['name', "description"]
    exclude = ('confirmed',)
    raw_id_fields = ('parent', 'root', '_created_by', '_updated_by')


class FoiLawAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('name', 'meta', 'jurisdiction',)
    raw_id_fields = ('mediator',)


class JurisdictionAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}


class PublicBodyTopicAdmin(admin.ModelAdmin):
    pass

admin.site.register(PublicBody, PublicBodyAdmin)
admin.site.register(FoiLaw, FoiLawAdmin)
admin.site.register(Jurisdiction, JurisdictionAdmin)
admin.site.register(PublicBodyTopic, PublicBodyTopicAdmin)
