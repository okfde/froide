import logging
from collections.abc import Callable
from functools import partial
from pathlib import Path

from django.contrib.gis.geos import GEOSGeometry

from .models import GeoRegion

logger = logging.getLogger(__name__)


def update_georegion(wkb, tags, get_region_key=None):
    key = get_region_key(tags)
    if not key:
        return
    GeoRegion.objects.filter(region_identifier=key).update(
        geom_detail=GEOSGeometry(wkb, srid=4326),
        osm_tags=tags,
    )


def import_osm_pbf(
    pbf_file: Path,
    region_key_func: Callable[[dict[str, str]], str | None],
):
    try:
        import osmium
    except ImportError:
        logger.error(
            "osmium module is not installed. Please install it to use this feature."
        )
        return

    class AdminAreaHandler(osmium.SimpleHandler):
        def __init__(self, area_callback):
            osmium.SimpleHandler.__init__(self)

            self.fab = osmium.geom.WKBFactory()
            self.area_callback = area_callback

        def area(self, area):
            if "admin_level" in area.tags:
                try:
                    wkb = self.fab.create_multipolygon(area)
                except RuntimeError:
                    logger.warning(
                        "Failed to create multipolygon for %s with tags %s",
                        area.tags.get("name"),
                        area.tags,
                    )
                    return
                self.area_callback(wkb, dict(area.tags))

    area_handler = partial(update_georegion, get_region_key=region_key_func)
    handler = AdminAreaHandler(area_handler)
    handler.apply_file(pbf_file, locations=True, idx="flex_mem")
