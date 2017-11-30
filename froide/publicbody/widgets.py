import json

from django import forms

from .models import PublicBody


class PublicBodySelect(forms.Widget):
    input_type = "text"
    template_name = 'publicbody/_chooser.html'
    initial_search = None

    class Media:
        extend = False
        js = ('js/publicbody.js',)

    def set_initial_search(self, search):
        self.initial_search = search

    def get_context(self, name, value=None, attrs=None):
        pb, pb_desc = None, None
        if value is not None:
            try:
                pb = PublicBody.objects.get(pk=int(value))
                pb_desc = pb.get_label()
            except (ValueError, PublicBody.DoesNotExist):
                pass
        context = super(PublicBodySelect, self).get_context(name, value, attrs)
        context['widget'].update({
            'value_label': pb_desc,
            'search': self.initial_search,
            'publicbody': pb,
            'json': json.dumps({
                'fields': {
                    name: {
                        'value': value,
                        'objects': [pb.as_data()] if pb is not None else None
                    }
                }
            })
        })
        return context
