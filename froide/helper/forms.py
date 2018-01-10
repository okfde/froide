from django.utils.translation import ugettext_lazy as _
from django import forms
from django.contrib.admin.widgets import ForeignKeyRawIdWidget

from taggit.forms import TagField
from taggit.utils import edit_string_for_tags

from .widgets import TagAutocompleteWidget


class TagObjectForm(forms.Form):
    def __init__(self, *args, **kwargs):
        tags = kwargs.pop('tags', [])
        if tags:
            kwargs['initial'] = {'tags': edit_string_for_tags(tags)}

        autocomplete_url = kwargs.pop('autocomplete_url', None)
        if autocomplete_url is not None:
            self.tags_autocomplete_url = autocomplete_url

        super(TagObjectForm, self).__init__(*args, **kwargs)

        self.fields['tags'] = TagField(label=_("Tags"),
            widget=TagAutocompleteWidget(
                attrs={'placeholder': _('Tags')},
                autocomplete_url=self.tags_autocomplete_url
            ),
            help_text=_("Comma separated and quoted"))

    def save(self, obj):
        obj.tags.set(*self.cleaned_data['tags'])
        obj.save()


def get_fk_form_class(model, field, admin_site, queryset=None):
    remote_field = model._meta.get_field(field).remote_field
    if queryset is None:
        queryset = remote_field.model.objects.all()

    widget = ForeignKeyRawIdWidget(remote_field, admin_site)

    class ForeignKeyForm(forms.Form):
        obj = forms.ModelChoiceField(queryset=queryset,
                                     widget=widget)

    return ForeignKeyForm
