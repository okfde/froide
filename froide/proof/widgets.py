from django import forms

from froide.helper.templatetags.frontendbuild import get_frontend_files
from froide.helper.widgets import JSModulePath


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
        return context
