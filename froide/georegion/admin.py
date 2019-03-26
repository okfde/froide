from django.contrib.gis import admin

from froide.helper.admin_utils import ForeignKeyFilter

from .models import GeoRegion


class GeoRegionMixin(object):
    search_fields = ['name', 'region_identifier']
    list_display = ('name', 'kind', 'kind_detail', 'region_identifier')
    list_filter = (
        'kind', 'kind_detail',
        ('part_of', ForeignKeyFilter),
    )
    raw_id_fields = ('part_of',)
    readonly_fields = ('depth', 'numchild', 'path')


class GeoRegionAdmin(GeoRegionMixin, admin.GeoModelAdmin):
    pass


admin.site.register(GeoRegion, GeoRegionAdmin)
