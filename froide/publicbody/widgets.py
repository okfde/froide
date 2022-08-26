import json

from django import forms
from django.urls import reverse
from django.utils.translation import gettext as _

from froide.helper.content_urls import get_content_url
from froide.helper.templatetags.frontendbuild import get_frontend_build


def get_widget_context():
    return {
        "url": {
            "searchPublicBody": reverse("api:publicbody-search"),
            "listLaws": reverse("api:law-list"),
            "getPublicBody": reverse("api:publicbody-detail", kwargs={"pk": "0"}),
            "helpAbout": get_content_url("about"),
        },
        "i18n": {
            "missingPublicBody": _("Are we missing a public body?"),
            "publicBodySearchPlaceholder": _("Ministry of..."),
            "search": _("Search"),
            "searchPublicBodyLabel": _("Search for public authorities"),
            "examples": _("Examples:"),
            "environment": _("Environment"),
            "ministryOfLabour": _("Ministry of Labour"),
            "or": _("or"),
            "noPublicBodiesFound": _("No Public Bodies found for this query."),
            "letUsKnow": _("Please let us know!"),
        },
    }


class PublicBodySelect(forms.Widget):
    input_type = "text"
    template_name = "publicbody/_chooser.html"

    @property
    def media(self):
        build_info = get_frontend_build("publicbody.js")
        return forms.Media(css={"all": build_info["css"]}, js=build_info["js"])

    def set_initial_object(self, obj):
        self.object = obj

    def get_context(self, name, value=None, attrs=None):
        context = super().get_context(name, value, attrs)
        objects = None
        if hasattr(self, "object") and self.object:
            objects = [self.object.as_simple_data()]
        context["widget"].update(
            {
                "json": json.dumps(
                    {"fields": {name: {"value": value, "objects": objects}}}
                )
            }
        )
        context["config"] = json.dumps(get_widget_context())
        return context
