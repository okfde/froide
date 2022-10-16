from typing import Any, Dict, Optional, Union

from django import forms
from django.conf import settings
from django.http.request import QueryDict
from django.utils.datastructures import MultiValueDict

from django_filters.widgets import DateRangeWidget as DFDateRangeWidget
from django_filters.widgets import RangeWidget
from taggit.forms import TagWidget
from taggit.utils import parse_tags

from froide.helper.templatetags.frontendbuild import get_frontend_files


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


class AutocompleteMixin:
    template_name = "helper/forms/widgets/tag_autocomplete.html"
    max_item_count = -1
    use_tags = False

    def __init__(self, *args, **kwargs) -> None:
        self.autocomplete_url: Optional[str] = kwargs.pop("autocomplete_url", None)
        self.allow_new: bool = kwargs.pop("allow_new", True)
        self.query_param: str = kwargs.pop("query_param", "q")
        self.max_item_count: int = kwargs.pop("max_item_count", self.max_item_count)
        self.model: int = kwargs.pop("model", None)
        super().__init__(*args, **kwargs)

    @property
    def media(self):
        build_info = get_frontend_files("tagautocomplete.js")
        return forms.Media(css={"all": build_info["css"]}, js=build_info["js"])

    def get_context(self, name, value, attrs):
        ctx = super().get_context(name, value, attrs)
        ctx["autocomplete_url"] = self.autocomplete_url
        ctx["allow_new"] = self.allow_new
        ctx["query_param"] = self.query_param
        ctx["max_item_count"] = self.max_item_count
        if value is not None:
            if isinstance(value, str):
                ctx["values"] = [{"label": x, "value": x} for x in parse_tags(value)]
            else:
                if self.model:
                    value = self.model.objects.filter(pk__in=value)
                ctx["values"] = [
                    {"label": str(x), "value": str(x) if self.use_tags else x.pk}
                    for x in value
                ]
        else:
            ctx["values"] = []
        return ctx


class AutocompleteWidget(AutocompleteMixin, forms.TextInput):
    max_item_count = 1


class AutocompleteMultiWidget(AutocompleteWidget):
    max_item_count = -1

    def value_from_datadict(self, data, files, name):
        value = data.get(name)
        if value:
            return value.split(",")

    def format_value(self, value):
        return ",".join(str(v) for v in value) if value else ""


class TagAutocompleteWidget(AutocompleteMixin, TagWidget):
    template_name = "helper/forms/widgets/tag_autocomplete.html"
    max_item_count = -1
    use_tags = True

    def value_from_datadict(
        self, data: QueryDict, files: MultiValueDict, name: str
    ) -> str:
        """Force comma separation of tags by adding trailing comma"""
        val = data.get(name, None)
        if val is None:
            return ""
        return val + ","


class DateRangeWidget(DFDateRangeWidget):
    template_name = "helper/forms/widgets/daterange.html"

    def __init__(self) -> None:
        widgets = [
            forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        ]
        # Skip super class init!
        super(RangeWidget, self).__init__(widgets)


class ImageFileInput(forms.ClearableFileInput):
    template_name = "helper/forms/widgets/image.html"

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("attrs", {})
        kwargs["attrs"].update({"class": "form-control"})
        super().__init__(*args, **kwargs)
