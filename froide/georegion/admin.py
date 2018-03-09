from django.contrib.gis import admin

from .models import GeoRegion


class GeoRegionAdmin(admin.GeoModelAdmin):
    search_fields = ['name', 'region_identifier']
    list_display = ('name', 'kind', 'region_identifier')
    list_filter = ('kind',)
    raw_id_fields = ('part_of',)


admin.site.register(GeoRegion, GeoRegionAdmin)
