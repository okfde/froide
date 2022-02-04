from typing import Dict, Optional, Type

from django import forms
from django.contrib.admin.sites import AdminSite
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.db.models import Model, QuerySet
from django.utils.translation import gettext_lazy as _

from taggit.forms import TagField
from taggit.utils import edit_string_for_tags

from .widgets import TagAutocompleteWidget


class TagObjectForm(forms.Form):
    def __init__(self, *args, **kwargs) -> None:
        tags = kwargs.pop("tags", [])
        if tags:
            kwargs["initial"] = {"tags": edit_string_for_tags(tags)}

        autocomplete_url = kwargs.pop("autocomplete_url", "") or ""

        if hasattr(self, "tags_autocomplete_url"):
            if self.tags_autocomplete_url:
                autocomplete_url = self.tags_autocomplete_url

        super().__init__(*args, **kwargs)

        self.fields["tags"] = TagField(
            label=_("Tags"),
            widget=TagAutocompleteWidget(
                attrs={"placeholder": _("Tags")}, autocomplete_url=autocomplete_url
            ),
            required=False,
            help_text=_("Comma separated and quoted"),
        )

    def save(self, obj: Model) -> None:
        obj.tags.set(*[t[:100] for t in self.cleaned_data["tags"]])
        obj.save()


class FakeRelatedField:
    def __init__(self, name: str):
        self.name = name


class FakeRemoteField:
    limit_choices_to = None

    def __init__(self, model: Type[Model], name: Optional[str] = None) -> None:
        self.model = model
        self.name = name

    def get_related_field(self) -> FakeRelatedField:
        if self.name is None:
            return FakeRelatedField(self.model.__name__.lower())
        return FakeRelatedField(self.name)


class NonFieldForeignKeyRawIdWidget(ForeignKeyRawIdWidget):
    def url_parameters(self) -> Dict[str, str]:
        params = self.base_url_parameters()
        return params


def get_fk_raw_id_widget(
    model: Type[Model], admin_site: AdminSite, field_name: Optional[str] = None
) -> NonFieldForeignKeyRawIdWidget:
    remote_field = FakeRemoteField(model, name=field_name)
    return NonFieldForeignKeyRawIdWidget(remote_field, admin_site)


def get_fake_fk_form_class(
    model: Type[Model], admin_site: AdminSite, queryset: Optional[QuerySet] = None
) -> forms.Form:
    widget = get_fk_raw_id_widget(model, admin_site)

    if queryset is None:
        queryset = model.objects.all()

    class ForeignKeyForm(forms.Form):
        obj = forms.ModelChoiceField(queryset=queryset, widget=widget)

    return ForeignKeyForm
