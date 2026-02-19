from django.contrib.gis.geos import MultiPolygon

import factory
from factory.django import DjangoModelFactory

from froide.georegion.models import GeoRegion
from froide.helper.text_utils import slugify


class GeoRegionFactory(DjangoModelFactory):
    class Meta:
        model = GeoRegion

    name = factory.Sequence(lambda n: "GeoRegion {0}".format(n))
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    kind = "country"
    geom = MultiPolygon()
    depth = 1
    path = factory.Sequence(lambda n: f"{n:04d}")
