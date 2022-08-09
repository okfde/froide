from typing import Any, Dict, Optional, Union

from django import forms
from django.conf import settings
from django.http.request import QueryDict
from django.utils.datastructures import MultiValueDict

from django_filters.widgets import DateRangeWidget as DFDateRangeWidget
from django_filters.widgets import RangeWidget
from taggit.forms import TagWidget
from taggit.utils import parse_tags

from froide.helper.templatetags.frontend import get_frontend_build


class BootstrapChoiceMixin(object):
    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("attrs", {})
        kwargs["attrs"].update({"class": "form-check-input"})
        super().__init__(*args, **kwargs)


class BootstrapCheckboxInput(BootstrapChoiceMixin, forms.CheckboxInput):
    pass


class BootstrapCheckboxSelectMultiple(
    BootstrapChoiceMixin, forms.CheckboxSelectMultiple
):
    pass


class BootstrapRadioSelect(BootstrapChoiceMixin, forms.RadioSelect):
    template_name = "helper/forms/widgets/radio.html"
    option_template_name = "helper/forms/widgets/radio_option.html"


class InlineBootstrapRadioSelect(BootstrapChoiceMixin, forms.RadioSelect):
    template_name = "helper/forms/widgets/radio.html"
    option_template_name = "helper/forms/widgets/radio_option_inline.html"


class BootstrapSelect(forms.Select):
    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("attrs", {})
        kwargs["attrs"].update({"class": "form-select"})
        super().__init__(*args, **kwargs)


class BootstrapFileInput(forms.FileInput):
    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("attrs", {})
        kwargs["attrs"].update({"class": "form-control"})
        super().__init__(*args, **kwargs)


class PriceInput(forms.TextInput):
    template_name = "helper/forms/widgets/price_input.html"

    def get_context(
        self, name: str, value: Optional[Union[float, str]], attrs: Dict[str, str]
    ) -> Dict[str, Any]:
        ctx = super().get_context(name, value, attrs)
        ctx["widget"].setdefault("attrs", {})
        ctx["widget"]["attrs"]["class"] = "form-control col-3"
        ctx["widget"]["attrs"]["pattern"] = "[\\d\\.,]*"
        ctx["currency"] = settings.FROIDE_CONFIG["currency"]
        return ctx


class TagAutocompleteWidget(TagWidget):
    template_name = "helper/forms/widgets/tag_autocomplete.html"

    def __init__(self, *args, **kwargs) -> None:
        self.autocomplete_url: Optional[str] = kwargs.pop("autocomplete_url", None)
        super().__init__(*args, **kwargs)

    @property
    def media(self):
        build_info = get_frontend_build("tagautocomplete.js")
        return forms.Media(css={"all": build_info["css"]}, js=build_info["js"])

    def value_from_datadict(
        self, data: QueryDict, files: MultiValueDict, name: str
    ) -> str:
        """Force comma separation of tags by adding trailing comma"""
        val = data.get(name, None)
        if val is None:
            return ""
        return val + ","

    def get_context(self, name, value, attrs):
        ctx = super().get_context(name, value, attrs)
        ctx["autocomplete_url"] = self.autocomplete_url
        if value is not None:
            if isinstance(value, str):
                ctx["tags"] = parse_tags(value)
            else:
                ctx["tags"] = [v.name for v in value]
        else:
            ctx["tags"] = []
        return ctx


class DateRangeWidget(DFDateRangeWidget):
    template_name = "helper/forms/widgets/daterange.html"

    def __init__(self) -> None:
        widgets = [
            forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        ]
        # Skip super class init!
        super(RangeWidget, self).__init__(widgets)
