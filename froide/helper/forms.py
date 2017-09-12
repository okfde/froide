from django.utils.translation import ugettext_lazy as _
from django.urls import reverse
from django import forms
from django.contrib.admin.widgets import ForeignKeyRawIdWidget

from taggit.forms import TagField
from taggit.utils import edit_string_for_tags

from .widgets import TagAutocompleteTagIt


class TagObjectForm(forms.Form):
    def __init__(self, obj, *args, **kwargs):
        self.obj = obj
        if obj is None:
            tags = kwargs.pop('tags')
        else:
            tags = obj.tags.all()

        if kwargs.get('resource_name'):
            self.resource_name = kwargs.pop('resource_name')

        kwargs['initial'] = {'tags': edit_string_for_tags([o for o in tags])}
        super(TagObjectForm, self).__init__(*args, **kwargs)

        self.fields['tags'] = TagField(label=_("Tags"),
            widget=TagAutocompleteTagIt(
                attrs={'placeholder': _('Tags')},
                autocomplete_url=reverse('api_get_tags_autocomplete', kwargs={
                    'api_name': 'v1',
                    'resource_name': self.resource_name}
                )),
            help_text=_("Comma separated and quoted"))

    def save(self):
        self.obj.tags.set(*self.cleaned_data['tags'])
        self.obj.save()


def get_fk_form_class(model, field, admin_site, queryset=None):
    remote_field = model._meta.get_field(field).remote_field
    if queryset is None:
        queryset = remote_field.model.objects.all()

    widget = ForeignKeyRawIdWidget(remote_field, admin_site)

    class ForeignKeyForm(forms.Form):
        obj = forms.ModelChoiceField(queryset=queryset,
                                     widget=widget)

    return ForeignKeyForm
