import json

from django import forms
from django.utils.translation import gettext as _

from froide.helper.templatetags.frontendbuild import get_frontend_files
from froide.helper.widgets import JSModulePath


def get_widget_context():
    return {
        "i18n": {
            "orUploadNewProof": _("or upload a new proof"),
            "undo": _("Undo"),
            "reset": _("Reset"),
            "redactionWarning": _(
                "When you upload an identity document, please redact all information except your name, the city and the validity date. After selecting an image, you can apply redactions to it."
            ),
            "redactionInstructions": _(
                "Click or touch and drag over the image to redact parts of it."
            ),
        },
    }


class ProofImageWidget(forms.widgets.FileInput):
    input_type = "file"
    template_name = "proof/widget.html"

    @property
    def media(self):
        build_info = get_frontend_files("proofupload.js")
        return forms.Media(
            css={"all": build_info["css"]},
            js=[JSModulePath(src) for src in build_info["js"]],
        )

    def get_context(self, name, value=None, attrs=None):
        context = super().get_context(name, value, attrs)
        context["config"] = json.dumps(get_widget_context())
        return context
