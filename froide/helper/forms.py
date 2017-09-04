from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django import forms

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
