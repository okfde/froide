from django import forms
from django.template.loader import render_to_string
from django.conf import settings

from publicbody.models import PublicBody

class PublicBodySelect(forms.Widget):
    def __init__(self, attrs=None):
        super(PublicBodySelect, self).__init__(attrs)

    def render(self, name, value=None, attrs=None, choices=()):
        pb_desc = None
        if value is not None:
            try:
                pb = PublicBody.objects.get(pk=int(value))
                pb_desc = pb.get_label()
            except (ValueError, PublicBody.DoesNotExist):
                pass
        return render_to_string('publicbody/_chooser.html', { 'name': name, 'value': value,
            "value_label": pb_desc, "STATIC_URL": settings.STATIC_URL})
