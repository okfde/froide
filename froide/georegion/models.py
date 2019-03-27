from django.utils.translation import ugettext_lazy as _
from django.contrib.gis.db import models

from treebeard.mp_tree import MP_Node, MP_NodeManager


class GeoRegionManager(MP_NodeManager):
    pass


class GeoRegion(MP_Node):
    name = models.CharField(_('Name'), max_length=255)
    slug = models.SlugField(_('Slug'), max_length=255)

    description = models.TextField(blank=True)

    KIND_CHOICES = (
        ('country', _('country')),
        ('state', _('state')),
        ('admin_district', _('administrative district')),
        ('district', _('district')),
        ('admin_cooperation', _('administrative cooperation')),
        ('municipality', _('municipality')),
        ('borough', _('borough')),
        ('zipcode', _('zipcode')),
        ('admin_court_jurisdiction', _('administrative court jurisdiction')),
    )
    kind = models.CharField(_('Kind of Region'), max_length=255,
        choices=KIND_CHOICES
    )
    kind_detail = models.CharField(max_length=255, blank=True)
    level = models.IntegerField(default=0)
    region_identifier = models.CharField(max_length=255, blank=True)
    global_identifier = models.CharField(max_length=255, blank=True)

    area = models.FloatField(_('Area'), default=0.0)  # in Sqm
    population = models.IntegerField(null=True, blank=True)
    valid_on = models.DateTimeField(null=True, blank=True)

    geom = models.MultiPolygonField(_('geometry'), geography=True)
    gov_seat = models.PointField(_('gov seat'), null=True, blank=True, geography=True)

    part_of = models.ForeignKey('self', verbose_name=_('Part of'), null=True,
        on_delete=models.SET_NULL, blank=True, related_name='sub_regions'
    )

    node_order_by = ('name',)

    class Meta:
        verbose_name = _('Geo Region')
        verbose_name_plural = _('Geo Regions')
        ordering = ('name',)

    def __str__(self):
        return '%s (%s)' % (self.name, self.pk)

    def get_all_sub_regions(self):
        def get_subregions(region):
            for sub_region in region.sub_regions.all():
                yield sub_region
                yield from get_subregions(sub_region)
        yield from get_subregions(self)
