from django.contrib import admin
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

import floppyforms as forms

from froide.publicbody.models import (PublicBody,
    PublicBodyTag, TaggedPublicBody, FoiLaw, Jurisdiction)
from froide.helper.admin_utils import AdminTagAllMixIn
from froide.helper.widgets import TagAutocompleteTagIt


class PublicBodyAdminForm(forms.ModelForm):
    class Meta:
        model = PublicBody
        widgets = {
            'tags': TagAutocompleteTagIt(
                autocomplete_url=lambda: reverse('api_get_tags_autocomplete', kwargs={
                    'api_name': 'v1',
                    'resource_name': 'publicbody'}
                )),
        }


class PublicBodyAdmin(admin.ModelAdmin, AdminTagAllMixIn):
    form = PublicBodyAdminForm

    prepopulated_fields = {
        "slug": ("name",),
        'classification_slug': ('classification',)
    }
    list_display = ('name', 'email', 'url', 'tag_list', 'classification', 'jurisdiction',)
    list_filter = ('tags', 'jurisdiction', 'classification')
    filter_horizontal = ('laws',)
    list_max_show_all = 5000
    search_fields = ['name', "description", 'classification']
    exclude = ('confirmed',)
    raw_id_fields = ('parent', 'root', '_created_by', '_updated_by')

    autocomplete_resource_name = 'publicbody'

    actions = ['export_csv', 'remove_from_index', 'tag_all']

    def export_csv(self, request, queryset):
        return HttpResponse(PublicBody.export_csv(queryset),
            content_type='text/csv')
    export_csv.short_description = _("Export to CSV")

    def remove_from_index(self, request, queryset):
        from haystack import connections as haystack_connections

        for obj in queryset:
            for using in haystack_connections.connections_info.keys():
                backend = haystack_connections[using].get_backend()
                backend.remove(obj)

        self.message_user(request, _("Removed from search index"))
    remove_from_index.short_description = _("Remove from search index")


class FoiLawAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('name', 'meta', 'jurisdiction',)
    raw_id_fields = ('mediator',)
    filter_horizontal = ('combined',)


class JurisdictionAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}


class PublicBodyTagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_topic", "rank"]
    list_filter = ['is_topic', 'rank']
    ordering = ["rank", "name"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ["name"]}


class TaggedPublicBodyAdmin(admin.ModelAdmin):
    raw_id_fields = ('content_object', 'tag')


admin.site.register(PublicBody, PublicBodyAdmin)
admin.site.register(FoiLaw, FoiLawAdmin)
admin.site.register(Jurisdiction, JurisdictionAdmin)
admin.site.register(PublicBodyTag, PublicBodyTagAdmin)
admin.site.register(TaggedPublicBody, TaggedPublicBodyAdmin)
