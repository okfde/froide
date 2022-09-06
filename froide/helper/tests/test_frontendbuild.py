from django.test import TestCase
from django.test.utils import override_settings

from ..templatetags.frontendbuild import FrontendBuildLoader, get_frontend_files

MANIFEST_DATA = {
    "node_modules/froide/frontend/javascript/makerequest.js": {
        "file": "makerequest.js",
        "src": "node_modules/froide/frontend/javascript/makerequest.js",
        "isEntry": True,
        "imports": [
            "_user-terms.js",
            "_law-select.js",
        ],
        "css": ["css/makerequest.css"],
    },
    "node_modules/froide/frontend/javascript/makerequest.css": {
        "file": "css/makerequest.css",
        "src": "node_modules/froide/frontend/javascript/makerequest.css",
    },
    "_law-select.js": {"file": "law-select.js"},
    "_user-terms.js": {
        "file": "user-terms.js",
        "imports": ["_i18n-mixin.js"],
        "css": ["css/user-terms.css"],
    },
    "_i18n-mixin.js": {
        "file": "i18n-mixin.js",
        "css": ["css/mixin.css"],
    },
}


class TestFrontendBuild(TestCase):
    @override_settings(FRONTEND_DEBUG=True)
    def test_missing_entry_points_debug(self):
        frontend = FrontendBuildLoader()
        frontend.entry_points = frontend.generate_entry_points(MANIFEST_DATA)
        with self.assertRaises(KeyError):
            get_frontend_files("non_existant.js", frontend=frontend)

    @override_settings(FRONTEND_DEBUG=False)
    def test_missing_entry_points(self):
        frontend = FrontendBuildLoader()
        frontend.entry_points = frontend.generate_entry_points(MANIFEST_DATA)
        result = get_frontend_files("non_existant.js", frontend=frontend)
        self.assertEqual(result, {})

    @override_settings(FRONTEND_DEBUG=True)
    def test_entry_point_debug(self):
        frontend = FrontendBuildLoader()
        frontend.entry_points = frontend.generate_entry_points(MANIFEST_DATA)
        files = get_frontend_files("makerequest.js", frontend=frontend)
        self.assertEqual(
            files,
            {
                "js": ["node_modules/froide/frontend/javascript/makerequest.js"],
                "css": (),
            },
        )

    @override_settings(FRONTEND_DEBUG=False)
    def test_entry_point(self):
        frontend = FrontendBuildLoader()
        frontend.entry_points = frontend.generate_entry_points(MANIFEST_DATA)
        files = get_frontend_files("makerequest.js", frontend=frontend)
        self.assertEqual(
            files,
            {
                "js": ["makerequest.js"],
                "css": ["css/mixin.css", "css/user-terms.css", "css/makerequest.css"],
            },
        )
