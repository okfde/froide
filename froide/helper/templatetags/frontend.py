import json
import re
from typing import Dict, List, Optional, Tuple

from django import template
from django.conf import settings
from django.templatetags.static import static
from django.utils.safestring import mark_safe

from .block_helper import VAR_NAME, get_default_dict

register = template.Library()


ENTRY_POINT_RE = re.compile(r"^[\w-]+\.js$")
FRONTEND_DEBUG = settings.FRONTEND_DEBUG


class FrontendBuildLoader:
    def __init__(self):
        self.entry_points = None

    def get_entry_point(self, name):
        if self.entry_points is None:
            self.entry_points = self.load_manifest()
        return self.entry_points.get(name)

    def load_dev_manifest(self):
        """
        Dev manifest format is:

        """
        try:
            with open(settings.FRONTEND_BUILD_DIR / "manifest.dev.json") as f:
                manifest_data = json.load(f)
        except IOError as e:
            raise Exception("Please build frontend or run frontend dev server") from e
        return {
            "{}.js".format(entry_point): {"source": source_file}
            for entry_point, source_file in manifest_data["inputs"].items()
        }

    def load_manifest(self):
        try:
            with open(settings.FRONTEND_BUILD_DIR / "manifest.json") as f:
                manifest_data = json.load(f)
        except IOError:
            return self.load_dev_manifest()

        entry_points = {}
        for source_file, data in manifest_data.items():
            output_file = data["file"]
            if not ENTRY_POINT_RE.match(output_file):
                continue
            entry_points[output_file] = {
                "source": source_file,
                "js": [output_file],
                "css": data.get("css", ()),
            }
        return entry_points


frontend = FrontendBuildLoader()

FRONTEND_TEMPLATES = {
    "js": '<script type="module" src="{src}" crossorigin="anonymous"></script>',
    "css": '<link rel="stylesheet" type="text/css" href="{src}" crossorigin="anonymous"/>',
}

FrontendFiles = Dict[str, List[str]]
FrontendList = List[Tuple[str, List[str]]]


def get_frontend_build(name: str) -> FrontendFiles:
    data = frontend.get_entry_point(name)
    if data is None:
        if FRONTEND_DEBUG:
            raise KeyError(name)
        return {}

    if FRONTEND_DEBUG:
        source_file = data["source"]
        # Replace relative references from vite with symlink in node_modules
        source_file = source_file.replace("../", "node_modules/")
        return {
            "js": [
                FRONTEND_TEMPLATES["js"].format(
                    src=settings.FRONTEND_SERVER_URL + source_file
                )
            ],
            "css": (),
        }

    result = {"js": [], "css": []}

    for block_name, paths in data.items():
        if block_name not in result:
            continue
        for path in paths:
            static_path = static(path)
            output = FRONTEND_TEMPLATES[block_name].format(src=static_path)
            result[block_name].append(output)
    return result


@register.simple_tag(takes_context=True)
def addfrontendbuild(context, name: str) -> str:

    result = get_frontend_build(name)
    if not result:
        return ""

    if VAR_NAME not in context:
        context[VAR_NAME] = get_default_dict()

    for block, output_list in result.items():
        for output in output_list:
            context[VAR_NAME][block][output] = None

    return ""


@register.simple_tag
def getfrontendbuild(name) -> Optional[FrontendList]:
    result = get_frontend_build(name)
    if not result:
        return
    return list(result.items())


@register.simple_tag
def renderfrontendhmr() -> str:
    if FRONTEND_DEBUG:
        return mark_safe(
            """<script type="module" src="{server_url}@vite/client" crossorigin="anonymous"></script>""".format(
                server_url=settings.FRONTEND_SERVER_URL
            )
        )
    return ""
