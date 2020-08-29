from django.contrib.gis import admin
from django import forms
from django.utils.translation import gettext_lazy as _

from treebeard.forms import movenodeform_factory

from froide.helper.admin_utils import ForeignKeyFilter
from froide.helper.forms import get_fk_raw_id_widget

from .models import GeoRegion


class GeoRegionAdminForm(movenodeform_factory(GeoRegion)):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        widget = get_fk_raw_id_widget(GeoRegion, admin.site, field_name='id')
        self.fields['_ref_node_id'] = forms.IntegerField(
            required=False, label=_("Relative to"),
            widget=widget
        )

    @classmethod
    def mk_dropdown_tree(cls, model, for_node=None):
        return []


class GeoRegionMixin(object):
    form = GeoRegionAdminForm

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
