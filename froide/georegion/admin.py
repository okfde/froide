from django.contrib.gis import admin

from .models import GeoRegion


class GeoRegionMixin(object):
    search_fields = ['name', 'region_identifier']
    list_display = ('name', 'kind', 'kind_detail', 'region_identifier')
    list_filter = ('kind',)
    raw_id_fields = ('part_of',)


class GeoRegionAdmin(GeoRegionMixin, admin.GeoModelAdmin):
    pass


admin.site.register(GeoRegion, GeoRegionAdmin)
