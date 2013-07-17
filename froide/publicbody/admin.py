from django.contrib import admin
from django.http import HttpResponse
from django.utils.translation import ugettext as _

from froide.publicbody.models import (PublicBody, FoiLaw, PublicBodyTopic,
        Jurisdiction)


class PublicBodyAdmin(admin.ModelAdmin):
    prepopulated_fields = {
        "slug": ("name",),
        'classification_slug': ('classification',)
    }
    list_display = ('name', 'email', 'url', 'classification', 'topic', 'jurisdiction',)
    list_filter = ('topic', 'jurisdiction', 'classification')
    list_max_show_all = 5000
    search_fields = ['name', "description"]
    exclude = ('confirmed',)
    raw_id_fields = ('parent', 'root', '_created_by', '_updated_by')
    actions = ['export_csv']

    def export_csv(self, request, queryset):
        return HttpResponse(PublicBody.export_csv(queryset),
            content_type='text/csv')
    export_csv.short_description = _("Export to CSV")


class FoiLawAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('name', 'meta', 'jurisdiction',)
    raw_id_fields = ('mediator',)


class JurisdictionAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}


class PublicBodyTopicAdmin(admin.ModelAdmin):
    prepopulated_fields = {
        "slug": ("name",)
    }

admin.site.register(PublicBody, PublicBodyAdmin)
admin.site.register(FoiLaw, FoiLawAdmin)
admin.site.register(Jurisdiction, JurisdictionAdmin)
admin.site.register(PublicBodyTopic, PublicBodyTopicAdmin)
