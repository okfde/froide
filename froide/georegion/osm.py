import logging
from collections.abc import Callable
from functools import partial
from pathlib import Path

from django.contrib.gis.geos import GEOSGeometry
from django.db.models import Q

from .models import GeoRegion

logger = logging.getLogger(__name__)


def update_georegion(wkb, tags, get_region_query=None):
    query = get_region_query(tags)
    if not query:
        return
    GeoRegion.objects.filter(query).update(
        geom_detail=GEOSGeometry(wkb, srid=4326),
        osm_tags=tags,
    )


def import_osm_pbf(
    pbf_file: Path,
    region_query_func: Callable[[dict[str, str]], Q | None],
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

    area_handler = partial(update_georegion, get_region_query=region_query_func)
    handler = AdminAreaHandler(area_handler)
    handler.apply_file(pbf_file, locations=True, idx="flex_mem")
