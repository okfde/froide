import floppyforms as forms

from django.template.loader import render_to_string
from django.conf import settings
from django.utils.safestring import mark_safe

from .models import PublicBody, Jurisdiction


class PublicBodySelect(forms.Widget):
    initial_jurisdiction = None

    def set_initial_jurisdiction(self, juris):
        self.initial_jurisdiction = juris

    def render(self, name, value=None, attrs=None, choices=()):
        pb, pb_desc = None, None
        juris_widget = None
        jurisdictions = Jurisdiction.objects.get_visible()
        if value is not None:
            try:
                pb = PublicBody.objects.get(pk=int(value))
                pb_desc = pb.get_label()
            except (ValueError, PublicBody.DoesNotExist):
                pass
        if len(jurisdictions) > 1:
            attrs = {"id": "id_juris_%s" % name,
                "class": "search-public_bodies-jurisdiction"}
            choices = [(j.name, j.name) for j in jurisdictions]
            juris_widget = forms.Select(choices=choices, attrs=attrs)
            if pb is None:
                juris_widget = juris_widget.render('jurisdiction', self.initial_jurisdiction)
            else:
                juris_widget = juris_widget.render('jurisdiction', pb.jurisdiction.name)
            juris_widget = mark_safe(juris_widget)
        return render_to_string('publicbody/_chooser.html', {'name': name,
            'value': value, "value_label": pb_desc,
            'juris_widget': juris_widget,
            'STATIC_URL': settings.STATIC_URL})
